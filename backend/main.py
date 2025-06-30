from fastapi import FastAPI, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
import PyPDF2
import io
import re
from typing import List, Optional, Dict, Any
import os
import json
import asyncio
import httpx
from fuzzywuzzy import fuzz

# --- LLM Integration ---
import google.generativeai as genai
from openai import OpenAI

# --- Database and Schemas ---
import models
import schemas
from database import SessionLocal, engine

# --- Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

deepseek_client = None
if DEEPSEEK_API_KEY:
    deepseek_client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com/v1"
    )

# --- FastAPI App Initialization ---
models.Base.metadata.create_all(bind=engine)
app = FastAPI()

origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- LLM Abstraction Layer ---
class LLMClient:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.is_gemini = "gemini" in model_name
        self.is_deepseek = "deepseek" in model_name

        if self.is_gemini:
            if not GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY is not configured.")
            self.model = genai.GenerativeModel(self.model_name)
        elif self.is_deepseek:
            if not deepseek_client:
                raise ValueError("DEEPSEEK_API_KEY is not configured.")
            self.model = deepseek_client
        else:
            raise ValueError(f"Unsupported model: {model_name}")

    def _execute_prompt(self, prompt: str) -> str:
        try:
            if self.is_gemini:
                response = self.model.generate_content(prompt)
                return response.text
            elif self.is_deepseek:
                chat_completion = self.model.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=4096,
                )
                return chat_completion.choices[0].message.content
        except Exception as e:
            print(f"Error executing prompt with {self.model_name}: {e}")
            return f"Error: {e}"
        return ""

    def parse_single_reference(self, ref_text: str) -> schemas.Reference:
        prompt = f"""
        You are an expert academic librarian. Your task is to parse a raw academic citation string and return a structured JSON object.
        The JSON object must contain the following fields: "authors" (a list of strings), "year" (an integer), "title" (a string), and "source" (a string, which is the journal, conference, or publisher).
        If a field cannot be found, its value should be null.
        Do not return any text other than the JSON object itself.
        Citation to parse: "{ref_text}"
        JSON output:
        """
        response_text = self._execute_prompt(prompt)
        try:
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not match:
                raise ValueError("No JSON object found in the AI response.")
            
            parsed_data = json.loads(match.group(0))
            return schemas.Reference(
                raw_text=ref_text,
                authors=parsed_data.get("authors"),
                year=parsed_data.get("year"),
                title=parsed_data.get("title"),
                source=parsed_data.get("source")
            )
        except Exception as e:
            return schemas.Reference(raw_text=ref_text, title=f"Error parsing with AI: {str(e)}")

    def analyze_unverified_reference(self, reference: schemas.Reference) -> str:
        prompt = f"""
        You are an expert academic librarian. A citation could not be found in online databases.
        Analyze the provided citation and determine the most likely reason for the verification failure.
        Choose from: "Incorrect Format", "Incomplete Information", "Ambiguous Title", "Non-Academic Source", "Potential Fabrication", "Not Found".
        Provide only the single most likely reason.
        Citation: "{reference.raw_text}"
        Parsed Title: "{reference.title}"
        Reason:
        """
        return self._execute_prompt(prompt).strip()

    def analyze_format_completeness(self, reference: schemas.Reference) -> Optional[str]:
        prompt = f"""
        You are an expert academic journal editor. Analyze the parsed fields of a citation for issues.
        Provide a single, concise suggestion for improvement if any issues are found. If the format is complete, return "None".
        Do not add any prefixes. Focus on missing fields or abbreviated source names.
        Parsed Citation: {{ "authors": {json.dumps(reference.authors)}, "year": {reference.year or "null"}, "title": {json.dumps(reference.title)}, "source": {json.dumps(reference.source)} }}
        Suggestion:
        """
        suggestion = self._execute_prompt(prompt).strip()
        return suggestion if "none" not in suggestion.lower() else None

    def rescue_parse_reference(self, ref_text: str) -> Optional[str]:
        prompt = f"""
        Previous parsing failed. Your single task is to identify and extract the main **title** of the academic paper from the text below.
        Return only the raw title as a single line of plain text.
        Raw Text: "{ref_text}"
        Title:
        """
        title = self._execute_prompt(prompt).strip()
        return title if title else None

    def extract_paper_metadata(self, text: str) -> Optional[Dict[str, Any]]:
        prompt = f"""
        You are a document analysis expert. Analyze the text from the first page of an academic paper and extract its metadata.
        Return a JSON object with "title", "authors", "year", and "affiliation". If a field is not found, its value must be `null`.
        Text to analyze: "{text[:4000]}"
        JSON output:
        """
        response_text = self._execute_prompt(prompt)
        try:
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except Exception as e:
            print(f"Metadata extraction error: {e}")
        return None

# --- PDF and Reference Parsing Utilities ---
def find_references_section(text: str) -> str:
    reference_keywords = ["references", "bibliography", "works cited", "literature cited", "參考文獻"]
    last_found_pos = -1
    for keyword in reference_keywords:
        pattern = re.compile(r"^\s*" + re.escape(keyword), re.IGNORECASE | re.MULTILINE)
        matches = list(pattern.finditer(text))
        if matches:
            last_match_pos = matches[-1].start()
            if last_match_pos > last_found_pos:
                last_found_pos = last_match_pos
    return text[last_found_pos:] if last_found_pos != -1 else ""

def parse_references(text: str) -> List[str]:
    if not text: return []
    pattern = re.compile(r"^\s*(\[\d+\]|\d+\.)", re.MULTILINE)
    if not pattern.search(text):
        lines = text.strip().split('\n')
        return [line.strip() for line in lines[1:] if line.strip()]
    
    split_text = pattern.split(text)
    references = [(split_text[i] + split_text[i+1]).strip().replace('\n', ' ') for i in range(1, len(split_text), 2)]
    return references

# --- Verification Logic ---
async def verify_reference(reference: schemas.Reference, llm_client: LLMClient) -> schemas.Reference:
    """
    Verifies a reference using a multi-step, resilient strategy.
    """
    # Step 0: Initial Status and Error Checks
    if reference.title and "Error parsing with AI" in reference.title:
        reference.status = "Format Error"
        reference.verification_score = 0
        return reference

    # Step 1: DOI Parsing and Direct Verification
    doi_match = re.search(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', reference.raw_text, re.IGNORECASE)
    if doi_match:
        doi = doi_match.group(0)
        try:
            await asyncio.sleep(0.1)
            async with httpx.AsyncClient() as client:
                response = await client.head(f"https://doi.org/{doi}", timeout=10.0, follow_redirects=True)
                if response.status_code == 200:
                    reference.status = "Verified"
                    reference.verified_doi = doi
                    reference.source = "DOI Verified"
                    reference.verification_score = 100
                    return reference
        except Exception as e:
            print(f"DOI verification error for '{doi}': {type(e).__name__} - {e}")

    # Step 2: Custom Rules for Trusted Sources
    raw_text_lower = reference.raw_text.lower()
    source_lower = (reference.source or "").lower()
    if "arxiv" in raw_text_lower or "arxiv" in source_lower:
        reference.status = "Verified"; reference.source = "arXiv"; reference.verification_score = 85; return reference
    if "ieee" in raw_text_lower or "ieee" in source_lower:
        reference.status = "Verified"; reference.source = "IEEE Publication"; reference.verification_score = 85; return reference
    if "proceedings" in raw_text_lower or "conference" in raw_text_lower:
        reference.status = "Verified"; reference.source = "Conference Paper"; reference.verification_score = 85; return reference

    # Step 3: Sequential API Verification
    api_verifiers = [
        ("CrossRef", "https://api.crossref.org/works", 95),
        ("Semantic Scholar", "https://api.semanticscholar.org/graph/v1/paper/search", 90),
        ("OpenAlex", "https://api.openalex.org/works", 90)
    ]

    for name, url, score_value in api_verifiers:
        if reference.title:
            try:
                await asyncio.sleep(0.1)
                if name == "CrossRef":
                    params = {"query.bibliographic": reference.title, "rows": 1}
                    if reference.authors: params["query.author"] = " ".join(reference.authors)
                elif name == "Semantic Scholar":
                    params = {"query": f"{(' '.join(reference.authors or []))} {reference.title}", "limit": 1, "fields": "title,authors,year,venue,publicationVenue,externalIds"}
                else: # OpenAlex
                    params = {"search": f"{(' '.join(reference.authors or []))} {reference.title}", "per_page": 1}

                async with httpx.AsyncClient() as client:
                    response = await client.get(url, params=params, timeout=10.0)

                if response.status_code == 200:
                    data = response.json()
                    if (name == "CrossRef" and data['message']['items']) or \
                       (name == "Semantic Scholar" and data.get('data')) or \
                       (name == "OpenAlex" and data.get('results')):
                        
                        item = data['message']['items'][0] if name == "CrossRef" else (data['data'][0] if name == "Semantic Scholar" else data['results'][0])
                        api_title = item.get('title', [''])[0] if name == "CrossRef" else item.get('title', '')
                        
                        score = fuzz.token_set_ratio(reference.title.lower(), api_title.lower())
                        if score > 85:
                            reference.status = "Verified"
                            reference.verification_score = score_value
                            if name == "CrossRef":
                                reference.verified_doi = item.get('DOI')
                                reference.source = f"CrossRef: {', '.join(item.get('container-title', []))}"
                            elif name == "Semantic Scholar":
                                reference.verified_doi = item.get('externalIds', {}).get('DOI', 'N/A')
                                reference.source = f"Semantic Scholar: {item.get('venue') or item.get('publicationVenue', {}).get('name', '')}"
                            else: # OpenAlex
                                reference.verified_doi = item.get('doi', 'N/A').replace("https://doi.org/", "")
                                reference.source = f"OpenAlex: {item.get('host_venue', {}).get('display_name', '')}"
                            return reference
            except Exception as e:
                print(f"{name} API error for '{reference.title}': {type(e).__name__} - {e}")

    # --- Step 4: Final Analysis by AI ---
    reference.status = await asyncio.to_thread(llm_client.analyze_unverified_reference, reference)
    reference.verification_score = 0
    return reference

# --- Main Streaming Endpoint ---
from fastapi.responses import StreamingResponse

@app.post("/stream-verify/")
async def stream_verify_endpoint(file: UploadFile = File(...), model_name: str = Form("gemini-1.5-pro")):
    try:
        pdf_content = await file.read()
    except Exception as e:
        async def error_generator():
            yield f"data: {json.dumps({'type': 'error', 'payload': {'message': f'Failed to read uploaded file: {e}'}})}\n\n"
        return StreamingResponse(error_generator(), media_type="text/event-stream")

    return StreamingResponse(stream_verification_process(pdf_content, model_name), media_type="text/event-stream")

async def stream_verification_process(pdf_content: bytes, model_name: str):
    def yield_event(event_type: str, data: dict):
        return f"data: {json.dumps({'type': event_type, 'payload': data})}\n\n"

    try:
        llm_client = LLMClient(model_name)
        yield yield_event("status", {"message": f"Using model: {model_name}"})

        yield yield_event("status", {"message": "Reading and parsing PDF..."})
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
        first_page_text = pdf_reader.pages[0].extract_text()

        yield yield_event("status", {"message": "Extracting paper metadata..."})
        metadata = await asyncio.to_thread(llm_client.extract_paper_metadata, first_page_text)
        if metadata:
            yield yield_event("metadata", metadata)

        full_text = first_page_text + "".join([page.extract_text() for page in pdf_reader.pages[1:]])
        references_text = find_references_section(full_text)
        
        if not references_text:
            # ... (handle no references found)
            return

        references_list = parse_references(references_text)
        total_refs = len(references_list)
        yield yield_event("status", {"message": f"Found {total_refs} references. Starting parsing..."})

        parsed_references = []
        for i, ref_text in enumerate(references_list):
            yield yield_event("status", {"message": f"Parsing reference {i+1}/{total_refs}..."})
            parsed_ref = await asyncio.to_thread(llm_client.parse_single_reference, ref_text)
            parsed_references.append(parsed_ref)
            await asyncio.sleep(0.05)

        yield yield_event("status", {"message": "Checking for parsing errors and attempting rescue..."})
        for i, ref in enumerate(parsed_references):
            if not ref.title:
                rescued_title = await asyncio.to_thread(llm_client.rescue_parse_reference, ref.raw_text)
                if rescued_title:
                    ref.title = rescued_title
                    yield yield_event("status", {"message": f"Rescued title for reference {i+1}!"})
        
        yield yield_event("status", {"message": "Analyzing reference formats..."})
        for ref in parsed_references:
            ref.format_suggestion = await asyncio.to_thread(llm_client.analyze_format_completeness, ref)
            await asyncio.sleep(0.05)

        summary_counts = {'verified': 0, 'notFound': 0, 'error': 0}
        for i, ref in enumerate(parsed_references):
            yield yield_event("status", {"message": f"Verifying reference {i+1}/{total_refs}: {ref.title[:50]}..."})
            verified_ref = await verify_reference(ref, llm_client)
            
            if verified_ref.status == "Verified":
                summary_counts['verified'] += 1
            elif verified_ref.status == "Format Error":
                summary_counts['error'] += 1
            else:
                summary_counts['notFound'] += 1
            
            yield yield_event("reference", verified_ref.dict())
            
            summary_payload = {
                'total_references': total_refs,
                'verified_count': summary_counts['verified'],
                'not_found_count': summary_counts['notFound'],
                'format_error_count': summary_counts['error']
            }
            yield yield_event("summary", summary_payload)
            await asyncio.sleep(0.1)

        yield yield_event("end", {"message": "Verification process complete."})

    except Exception as e:
        yield yield_event("error", {"message": f"An unexpected error occurred: {str(e)}"})