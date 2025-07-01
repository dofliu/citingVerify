import io
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register Chinese font
# Use the font installed in the Dockerfile
pdfmetrics.registerFont(TTFont('WQYZenHei', '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'))

def generate_pdf_report(data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Define styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ChineseTitle', parent=styles['h1'], fontName='WQYZenHei'))
    styles.add(ParagraphStyle(name='ChineseBody', parent=styles['BodyText'], fontName='WQYZenHei'))
    styles.add(ParagraphStyle(name='ChineseH2', parent=styles['h2'], fontName='WQYZenHei'))
    styles.add(ParagraphStyle(name='ChineseH4', parent=styles['h4'], fontName='WQYZenHei'))

    is_chinese = data.get('language', 'en').startswith('zh')

    # --- Translations ---
    translations = {
        'report_title': "文獻引用驗證報告" if is_chinese else "Citation Verification Report",
        'paper_info': "論文資訊" if is_chinese else "Paper Information",
        'title': "標題" if is_chinese else "Title",
        'authors': "作者" if is_chinese else "Authors",
        'year': "年份" if is_chinese else "Year",
        'affiliation': "機構" if is_chinese else "Affiliation",
        'verification_summary': "驗證摘要" if is_chinese else "Verification Summary",
        'model_used': "使用模型" if is_chinese else "Model Used",
        'total_references': "總引用數" if is_chinese else "Total References",
        'verified': "已驗證" if is_chinese else "Verified",
        'not_found': "未找到" if is_chinese else "Not Found",
        'format_error': "格式錯誤" if is_chinese else "Format Error",
        'detailed_results': "詳細結果" if is_chinese else "Detailed Results",
        'table_status': "狀態" if is_chinese else "Status",
        'table_authors': "作者" if is_chinese else "Authors",
        'table_year': "年份" if is_chinese else "Year",
        'table_title': "標題" if is_chinese else "Title",
        'table_source': "來源" if is_chinese else "Source",
    }

    story = []

    # --- Report Title ---
    title_style = styles['ChineseTitle'] if is_chinese else styles['h1']
    story.append(Paragraph(translations['report_title'], title_style))
    story.append(Spacer(1, 0.2*inch))

    # --- Paper Metadata and Verification Summary ---
    meta_style = styles['ChineseBody'] if is_chinese else styles['BodyText']
    h2_style = styles['ChineseH2'] if is_chinese else styles['h2']
    
    story.append(Paragraph(translations['paper_info'], h2_style))
    meta = data.get('paperMetadata', {})
    meta_text = f"""
    <b>{translations['title']}:</b> {meta.get('title', 'N/A')}<br/>
    <b>{translations['authors']}:</b> {', '.join(meta.get('authors') or [])}<br/>
    <b>{translations['year']}:</b> {meta.get('year', 'N/A')} | <b>{translations['affiliation']}:</b> {meta.get('affiliation', 'N/A')}
    """
    story.append(Paragraph(meta_text, meta_style))
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph(translations['verification_summary'], h2_style))
    summary_data = data['summary']
    summary_text = f"""
    <b>{translations['model_used']}:</b> {data.get('model_name', 'N/A')}<br/>
    <b>{translations['total_references']}:</b> {summary_data['total_references']} | 
    <b>{translations['verified']}:</b> {summary_data['verified_count']} | 
    <b>{translations['not_found']}:</b> {summary_data['not_found_count']} | 
    <b>{translations['format_error']}:</b> {summary_data['format_error_count']}
    """
    story.append(Paragraph(summary_text, meta_style))
    story.append(Spacer(1, 0.2*inch))

    # --- Pie Chart ---
    pie_data = [
        summary_data['verified_count'],
        summary_data['not_found_count'],
        summary_data['format_error_count']
    ]
    if any(pie_data): # Only show pie chart if there is data
        pie = Pie()
        pie.x = 150
        pie.y = 5
        pie.width = 100
        pie.height = 100
        pie.data = pie_data
        pie.labels = [
            f"{translations['verified']} ({summary_data['verified_count']})",
            f"{translations['not_found']} ({summary_data['not_found_count']})",
            f"{translations['format_error']} ({summary_data['format_error_count']})"
        ]
        pie.slices.strokeWidth = 0.5
        pie.slices[0].fillColor = colors.HexColor('#28a745')
        pie.slices[1].fillColor = colors.HexColor('#dc3545')
        pie.slices[2].fillColor = colors.HexColor('#ffc107')
        
        drawing = Drawing(300, 120)
        drawing.add(pie)
        story.append(drawing)
    story.append(Spacer(1, 0.2*inch))

    # --- Detailed Results Table ---
    story.append(Paragraph(translations['detailed_results'], h2_style))
    
    body_style = styles['ChineseBody'] if is_chinese else styles['BodyText']
    header_style = styles['ChineseH4'] if is_chinese else styles['h4']

    header = [Paragraph(cell, header_style) for cell in [
        translations['table_status'], translations['table_authors'], translations['table_year'], 
        translations['table_title'], translations['table_source']
    ]]
    table_data = [header]

    for ref in data['references']:
        table_data.append([
            Paragraph(str(ref.get('status', 'N/A')), body_style),
            Paragraph(', '.join(ref.get('authors') or []), body_style),
            Paragraph(str(ref.get('year', 'N/A')), body_style),
            Paragraph(str(ref.get('title', 'N/A')), body_style),
            Paragraph(str(ref.get('source', 'N/A')), body_style)
        ])

    table = Table(table_data, colWidths=[1*inch, 2*inch, 0.5*inch, 3.5*inch, 2*inch], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F81BD')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'WQYZenHei' if is_chinese else 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        # Zebra stripes
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#DCE6F1')),
    ]))

    # Apply zebra stripes to the rest of the table
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            bg_color = colors.white
        else:
            bg_color = colors.HexColor('#DCE6F1')
        table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), bg_color)]))

    story.append(table)

    doc.build(story)
    buffer.seek(0)
    return buffer
