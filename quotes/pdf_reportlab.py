from decimal import Decimal
from io import BytesIO
import os
import unicodedata
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
PAGE_W, PAGE_H = A4
PDF_FONT_BODY = 'Helvetica'
PDF_FONT_BOLD = 'Helvetica-Bold'
_PDF_FONTS_INIT = False


def _register_quote_pdf_fonts(find):
    global PDF_FONT_BODY, PDF_FONT_BOLD, _PDF_FONTS_INIT
    if _PDF_FONTS_INIT:
        return
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    if 'QuotePdfSans' in pdfmetrics.getRegisteredFontNames():
        PDF_FONT_BODY = 'QuotePdfSans'
        PDF_FONT_BOLD = 'QuotePdfSans-Bold'
        _PDF_FONTS_INIT = True
        return

    def pair(reg, bold):
        if reg and bold and os.path.isfile(reg) and os.path.isfile(bold):
            return [(reg, bold)]
        return []

    candidates = []
    candidates += pair(os.environ.get('QUOTE_PDF_FONT_REGULAR'), os.environ.get('QUOTE_PDF_FONT_BOLD'))
    candidates += pair(find('fonts/NotoSans-Regular.ttf'), find('fonts/NotoSans-Bold.ttf'))
    try:
        from django.conf import settings as _dj_settings
        _base = getattr(_dj_settings, 'BASE_DIR', None)
        if _base is not None:
            _bf = Path(_base) / 'static' / 'fonts'
            candidates += pair(str(_bf / 'NotoSans-Regular.ttf'), str(_bf / 'NotoSans-Bold.ttf'))
    except Exception:
        pass
    candidates += pair('/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf', '/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf')
    candidates += pair('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
    if os.name == 'nt':
        w = os.environ.get('WINDIR', r'C:\Windows')
        candidates += pair(os.path.join(w, 'Fonts', 'arial.ttf'), os.path.join(w, 'Fonts', 'arialbd.ttf'))
    for reg, bold in candidates:
        try:
            pdfmetrics.registerFont(TTFont('QuotePdfSans', reg))
            pdfmetrics.registerFont(TTFont('QuotePdfSans-Bold', bold))
            PDF_FONT_BODY = 'QuotePdfSans'
            PDF_FONT_BOLD = 'QuotePdfSans-Bold'
            break
        except Exception:
            continue
    _PDF_FONTS_INIT = True


def _pdf_txt(s):
    if s is None:
        return ''
    return unicodedata.normalize('NFC', str(s))


def Y(y_from_top):
    return PAGE_H - y_from_top

def _img(c, path, x, y_bottom, w, h):
    if path and os.path.exists(path):
        c.drawImage(path, x, y_bottom, w, h, preserveAspectRatio=True, mask='auto')

def _truncate(s, max_len=45):
    s = _pdf_txt(s)
    return s[:max_len] + '…' if len(s) > max_len else s

def _truncate_to_width(c, s, max_width, font=None, size=7):
    s = _pdf_txt(s)
    if not s:
        return s
    if font is None:
        font = PDF_FONT_BODY
    c.setFont(font, size)
    if c.stringWidth(s) <= max_width:
        return s
    ellipsis = '…'
    while len(s) > 1 and c.stringWidth(s[:len(s) - 1] + ellipsis) > max_width:
        s = s[:-1]
    return s[:len(s) - 1] + ellipsis if len(s) > 1 else ellipsis

def _wrap_to_lines(c, s, max_width, font=None, size=7, max_lines=4):
    s = _pdf_txt(s)
    if not s:
        return []
    if font is None:
        font = PDF_FONT_BODY
    c.setFont(font, size)
    words = s.split()
    lines = []
    current = ''
    for w in words:
        test = (current + ' ' + w).strip() if current else w
        if c.stringWidth(test) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w if c.stringWidth(w) <= max_width else _truncate_to_width(c, w, max_width)
    if current:
        lines.append(current)
    return lines[:max_lines]

def _fmt_money(val):
    if val is None:
        return '$0.00'
    v = Decimal(str(val))
    return f'${v:,.2f}'

def _currency_suffix(moneda_code):
    c = (moneda_code or 'MXN').strip().upper()
    if c == 'USD':
        return ' USD'
    if c == 'MXN':
        return ' MXN'
    return f' {c}'

def _parse_terms(terms_text):
    result = {'payment': '', 'delivery': '', 'warranty': '', 'place': ''}
    if not terms_text or not str(terms_text).strip():
        return result
    text = str(terms_text).strip()
    parts = [p.strip() for p in text.replace('.', ';').split(';') if p.strip()]
    for p in parts:
        lower = p.lower()
        if lower.startswith('pago') or 'anticipo' in lower:
            result['payment'] = p
        elif lower.startswith('entrega') and 'lugar' not in lower:
            result['delivery'] = p
        elif 'garantía' in lower or 'garantia' in lower:
            result['warranty'] = p
        elif 'lugar' in lower:
            result['place'] = p
    return result

def build_quote_pdf(quote, company, vigencia_texto, issue_date_formatted):
    from django.contrib.staticfiles import finders
    from django.conf import settings as django_settings
    _register_quote_pdf_fonts(finders.find)
    company = {k: _pdf_txt(v) for k, v in dict(company or {}).items()}
    vigencia_texto = _pdf_txt(vigencia_texto)
    issue_date_formatted = _pdf_txt(issue_date_formatted)
    logo_path = finders.find('img/logo.png')
    hero_path = finders.find(getattr(django_settings, 'QUOTE_PDF_HEADER_IMAGE', 'img/quote_header_right.png'))
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))
    c.setTitle(f'Cotización {quote.quote_number}')
    cust = quote.customer
    contact = quote.contact
    col_text = f"{cust.neighborhood or ''} {cust.city or ''}".strip()
    moneda_display = quote.currency or 'MXN'
    moneda_suffix = _currency_suffix(moneda_display)
    M = 45
    LW = 120
    _img(c, logo_path, M, Y(95), LW, 55)
    INFO_X = 195
    c.setFont(PDF_FONT_BOLD, 8)
    c.drawString(INFO_X, Y(58), company.get('name', 'Sistemas de Conteo de Personas.'))
    c.setFont(PDF_FONT_BODY, 7)
    c.drawString(INFO_X, Y(68), company.get('street', 'Blvd. Paseo de la República No. 13020 Int. 1307'))
    c.drawString(INFO_X, Y(78), f"{company.get('colony', '')} {company.get('postal_code', '')}".strip())
    c.drawString(INFO_X, Y(88), f"Tel: {company.get('phone', '')}")
    c.drawString(INFO_X, Y(98), f"RFC: {company.get('rfc', '')}")
    c.drawString(INFO_X, Y(108), f"e-mail: {company.get('email', '')}")
    c.setFont(PDF_FONT_BOLD, 7)
    c.drawString(INFO_X, Y(118), company.get('website', 'www.sisconper.com'))
    BOX_X, BOX_Y, BOX_W, BOX_H = (M, 135, 135, 40)
    c.setLineWidth(2)
    c.rect(BOX_X, Y(BOX_Y + BOX_H), BOX_W, BOX_H)
    pad_x = 8
    top_pad = 10
    line_gap = 14
    y_num = BOX_Y + top_pad
    y_fecha = y_num + line_gap
    y_vig = y_fecha + line_gap
    c.setFont(PDF_FONT_BOLD, 7)
    c.drawString(BOX_X + pad_x, Y(y_num), 'Número:')
    c.drawString(BOX_X + pad_x, Y(y_fecha), 'Fecha:')
    c.drawString(BOX_X + pad_x, Y(y_vig), 'Vigencia:')
    c.setFont(PDF_FONT_BODY, 7)
    value_x = BOX_X + 55
    c.drawString(value_x, Y(y_num), quote.quote_number)
    c.drawString(value_x, Y(y_fecha), issue_date_formatted)
    c.drawString(value_x, Y(y_vig), vigencia_texto)
    CL_X, CL_Y, CL_W, CL_H = (195, 135, 215, 100)
    COT_W = 145
    COT_X = CL_X + CL_W
    MONEDA_H = 20
    LABEL_W = 68
    VAL_X = CL_X + LABEL_W + 6
    VAL_MAX_W = COT_X - VAL_X - 8
    c.setLineWidth(1)
    c.rect(CL_X, Y(CL_Y + CL_H), CL_W + COT_W, CL_H)
    c.line(COT_X, Y(CL_Y + CL_H), COT_X, Y(CL_Y))
    c.line(CL_X + LABEL_W, Y(CL_Y + CL_H), CL_X + LABEL_W, Y(CL_Y))
    BOTTOM_STRIP_H = 18
    LINE_Y = CL_Y + CL_H - BOTTOM_STRIP_H
    c.line(CL_X, Y(LINE_Y), CL_X + CL_W + COT_W, Y(LINE_Y))
    c.setFont(PDF_FONT_BOLD, 9)
    c.drawString(CL_X, Y(CL_Y - 5), 'CLIENTE')
    step = 7

    def _val(txt):
        return _truncate_to_width(c, txt, VAL_MAX_W)
    row_bottom = CL_Y + CL_H - 10
    c.setFont(PDF_FONT_BODY, 7)
    c.drawString(CL_X + 6, Y(row_bottom), 'e-mail:')
    c.setFillColorRGB(0.05, 0.35, 0.85)
    c.drawString(VAL_X, Y(row_bottom), _val(contact.email if contact else ''))
    c.setFillColorRGB(0, 0, 0)
    c.drawString(COT_X + 8, Y(row_bottom), 'Moneda')
    c.drawString(COT_X + 50, Y(row_bottom), moneda_display)
    row_start = CL_Y + 10
    c.setFont(PDF_FONT_BODY, 7)
    c.drawString(CL_X + 6, Y(row_start), 'Empresa:')
    c.setFont(PDF_FONT_BOLD, 7)
    c.drawString(VAL_X, Y(row_start), _truncate_to_width(c, cust.name, VAL_MAX_W, font=PDF_FONT_BOLD, size=7))
    c.setFont(PDF_FONT_BODY, 7)
    c.drawString(CL_X + 6, Y(row_start + step), 'Web:')
    c.setFillColorRGB(0.05, 0.35, 0.85)
    c.drawString(VAL_X, Y(row_start + step), _truncate_to_width(c, cust.website or '', VAL_MAX_W, size=7))
    c.setFillColorRGB(0, 0, 0)
    c.drawString(CL_X + 6, Y(row_start + step * 2), 'Calle y No.')
    c.drawString(VAL_X, Y(row_start + step * 2), _val(cust.street_address or ''))
    c.drawString(CL_X + 6, Y(row_start + step * 3), 'Col.')
    c.drawString(VAL_X, Y(row_start + step * 3), _val(col_text))
    c.drawString(CL_X + 6, Y(row_start + step * 4), 'C.P.')
    c.drawString(VAL_X, Y(row_start + step * 4), _val(cust.postal_code or ''))
    c.drawString(CL_X + 6, Y(row_start + step * 5), 'Tels.')
    c.drawString(VAL_X, Y(row_start + step * 5), _val(cust.phone or ''))
    c.drawString(CL_X + 6, Y(row_start + step * 6), 'Celular')
    celular = cust.mobile or (contact.mobile if contact else '') or ''
    c.drawString(VAL_X, Y(row_start + step * 6), _val(celular))
    c.drawString(CL_X + 6, Y(row_start + step * 7), 'Contacto:')
    c.drawString(VAL_X, Y(row_start + step * 7), _val(contact.full_name if contact else ''))
    c.drawString(CL_X + 6, Y(row_start + step * 8), 'Puesto:')
    c.drawString(VAL_X, Y(row_start + step * 8), _val(contact.position if contact else ''))
    cot_main = CL_Y + MONEDA_H + 12
    empresa_cotizada = _truncate_to_width(c, cust.name, COT_W - 16, font=PDF_FONT_BOLD, size=9)
    c.setFont(PDF_FONT_BOLD, 12)
    c.drawCentredString(COT_X + COT_W / 2, Y(cot_main), 'COTIZACIÓN')
    c.setFont(PDF_FONT_BOLD, 9)
    c.drawCentredString(COT_X + COT_W / 2, Y(cot_main + 20), empresa_cotizada)
    _img(c, hero_path, COT_X + COT_W - LW, Y(95), LW, 55)
    TABLE_TOP = 255
    TABLE_LEFT = 40
    TABLE_RIGHT = PAGE_W - 30
    COL_PARTIDA = TABLE_LEFT
    COL_PARTE = 78
    COL_DESC = 138
    COL_UNIT = 338
    COL_QTY = 382
    COL_PRICE_LEFT = 436
    COL_TOTAL_LEFT = 492
    COL_TOTAL_RIGHT = TABLE_RIGHT
    ROW_H = 20
    HEADER_Y = TABLE_TOP
    HEADER_H = 20
    pad = 6
    c.setFillColor(colors.HexColor('#1F7A8C'))
    c.rect(COL_PARTIDA, Y(HEADER_Y + HEADER_H), TABLE_RIGHT - COL_PARTIDA, HEADER_H, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont(PDF_FONT_BOLD, 7)
    header_text_y = HEADER_Y + 8
    pad = 6
    c.drawCentredString(COL_PARTIDA + (COL_PARTE - COL_PARTIDA) / 2, Y(header_text_y), _truncate_to_width(c, 'Partida', COL_PARTE - COL_PARTIDA - pad, font=PDF_FONT_BOLD))
    c.drawString(COL_PARTE + pad, Y(header_text_y), _truncate_to_width(c, 'No de parte', COL_DESC - COL_PARTE - pad, font=PDF_FONT_BOLD))
    c.drawString(COL_DESC + pad, Y(header_text_y), _truncate_to_width(c, 'Descripción', COL_UNIT - COL_DESC - pad, font=PDF_FONT_BOLD))
    c.drawCentredString(COL_UNIT + (COL_QTY - COL_UNIT) / 2, Y(header_text_y), _truncate_to_width(c, 'Unidad', COL_QTY - COL_UNIT - pad, font=PDF_FONT_BOLD))
    c.drawCentredString(COL_QTY + (COL_PRICE_LEFT - COL_QTY) / 2, Y(header_text_y), _truncate_to_width(c, 'Cantidad', COL_PRICE_LEFT - COL_QTY - pad, font=PDF_FONT_BOLD))
    c.drawCentredString(COL_PRICE_LEFT + (COL_TOTAL_LEFT - COL_PRICE_LEFT) / 2, Y(header_text_y), _truncate_to_width(c, 'PU', COL_TOTAL_LEFT - COL_PRICE_LEFT - pad, font=PDF_FONT_BOLD, size=7))
    c.drawCentredString(COL_TOTAL_LEFT + (COL_TOTAL_RIGHT - COL_TOTAL_LEFT) / 2, Y(header_text_y), _truncate_to_width(c, 'Total', COL_TOTAL_RIGHT - COL_TOTAL_LEFT - pad, font=PDF_FONT_BOLD))
    c.setFillColor(colors.black)
    items = list(quote.items.select_related('camera_model').order_by('id'))
    optional_rows = quote.get_optional_rows()
    y_row = HEADER_Y + HEADER_H + ROW_H
    partida = 1
    c.setLineWidth(0.5)
    W_PARTIDA = COL_PARTE - COL_PARTIDA - pad
    W_PARTE = COL_DESC - COL_PARTE - pad
    W_DESC = COL_UNIT - COL_DESC - pad
    W_UNIT = COL_QTY - COL_UNIT - pad
    W_QTY = COL_PRICE_LEFT - COL_QTY - pad
    W_PRICE = COL_TOTAL_LEFT - COL_PRICE_LEFT - pad
    W_TOTAL = COL_TOTAL_RIGHT - COL_TOTAL_LEFT - pad
    for item in items:
        cam = item.camera_model
        desc = cam.name or cam.model_code
        unidad = 'Pza.'
        c.setFont(PDF_FONT_BODY, 7)
        c.drawCentredString(COL_PARTIDA + W_PARTIDA / 2, Y(y_row), _truncate_to_width(c, str(partida), W_PARTIDA))
        c.drawString(COL_PARTE + pad, Y(y_row), _truncate_to_width(c, cam.model_code, W_PARTE))
        c.drawString(COL_DESC + pad, Y(y_row), _truncate_to_width(c, desc, W_DESC))
        c.drawCentredString(COL_UNIT + W_UNIT / 2, Y(y_row), _truncate_to_width(c, unidad, W_UNIT))
        c.drawCentredString(COL_QTY + W_QTY / 2, Y(y_row), _truncate_to_width(c, str(item.quantity), W_QTY))
        c.drawRightString(COL_TOTAL_LEFT - pad, Y(y_row), _truncate_to_width(c, _fmt_money(item.unit_price), W_PRICE))
        c.drawRightString(COL_TOTAL_RIGHT - pad, Y(y_row), _truncate_to_width(c, _fmt_money(item.line_subtotal), W_TOTAL))
        y_row += ROW_H
        partida += 1
    disc = quote.special_discount_amount or Decimal('0')
    if disc != 0:
        pct = quote.special_discount_percent or 0
        c.setFont(PDF_FONT_BOLD, 7)
        c.drawString(COL_DESC + pad, Y(y_row), _truncate_to_width(c, 'Descuento', W_DESC))
        c.drawCentredString(COL_UNIT + W_UNIT / 2, Y(y_row), 'Desc.')
        c.drawCentredString(COL_QTY + W_QTY / 2, Y(y_row), '1')
        c.drawRightString(COL_TOTAL_LEFT - pad, Y(y_row), _truncate_to_width(c, f'{pct}%', W_PRICE))
        c.drawRightString(COL_TOTAL_RIGHT - pad, Y(y_row), _truncate_to_width(c, f'-{_fmt_money(disc)}', W_TOTAL))
        y_row += ROW_H
    total_principal = quote.products_total_with_tax
    c.setFont(PDF_FONT_BOLD, 7)
    c.drawCentredString(COL_PRICE_LEFT + W_PRICE / 2, Y(y_row + 6), 'Total')
    c.drawRightString(COL_TOTAL_RIGHT - pad, Y(y_row + 6), _truncate_to_width(c, _fmt_money(total_principal) + moneda_suffix, W_TOTAL, size=7))
    y_row += ROW_H + 16
    SEP_LINE_GAP = 3
    SEP_MARGIN_BELOW = 9
    SEP_LINES_H = SEP_LINE_GAP + SEP_MARGIN_BELOW
    TABLE_BOTTOM_Y = 680
    if optional_rows:
        space_for_opts = SEP_LINES_H + (1 + len(optional_rows)) * ROW_H + 10
    else:
        space_for_opts = 0
    gap = max(0, TABLE_BOTTOM_Y - y_row - space_for_opts)
    y_row += gap
    if optional_rows:
        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(0.75)
        y_line1 = y_row
        y_line2 = y_row + SEP_LINE_GAP
        c.line(COL_PARTIDA, Y(y_line1), COL_TOTAL_RIGHT, Y(y_line1))
        c.line(COL_PARTIDA, Y(y_line2), COL_TOTAL_RIGHT, Y(y_line2))
        y_row = y_line2 + SEP_MARGIN_BELOW
        c.setFont(PDF_FONT_BOLD, 7)
        c.drawString(COL_DESC + pad, Y(y_row), 'Opcional')
        y_row += ROW_H
        for opt in optional_rows:
            c.setFont(PDF_FONT_BODY, 7)
            c.drawCentredString(COL_PARTIDA + W_PARTIDA / 2, Y(y_row), _truncate_to_width(c, str(opt.get('partida', partida)), W_PARTIDA))
            c.drawString(COL_PARTE + pad, Y(y_row), _truncate_to_width(c, '—', W_PARTE))
            c.drawString(COL_DESC + pad, Y(y_row), _truncate_to_width(c, opt.get('desc', ''), W_DESC))
            c.drawCentredString(COL_UNIT + W_UNIT / 2, Y(y_row), _truncate_to_width(c, 'Serv.', W_UNIT))
            c.drawCentredString(COL_QTY + W_QTY / 2, Y(y_row), _truncate_to_width(c, '1', W_QTY))
            c.drawRightString(COL_TOTAL_LEFT - pad, Y(y_row), _truncate_to_width(c, _fmt_money(opt.get('monto')), W_PRICE, size=7))
            c.setFont(PDF_FONT_BOLD, 7)
            c.drawRightString(COL_TOTAL_RIGHT - pad, Y(y_row), _truncate_to_width(c, _fmt_money(opt.get('monto')) + moneda_suffix, W_TOTAL))
            y_row += ROW_H
    BOTTOM_MARGIN = 60
    FOOTER_Y = 680
    FOOTER_H = PAGE_H - FOOTER_Y - BOTTOM_MARGIN
    FOOTER_H = min(FOOTER_H, 100)
    TABLE_BOTTOM = FOOTER_Y
    table_bottom_y = TABLE_BOTTOM
    c.setLineWidth(0.5)
    tbl_bottom = Y(table_bottom_y)
    tbl_top = Y(HEADER_Y + HEADER_H)
    for col_x in (COL_PARTIDA, COL_PARTE, COL_DESC, COL_UNIT, COL_QTY, COL_PRICE_LEFT, COL_TOTAL_LEFT, COL_TOTAL_RIGHT):
        c.line(col_x, tbl_bottom, col_x, tbl_top)
    c.line(COL_PARTIDA, tbl_bottom, COL_TOTAL_RIGHT, tbl_bottom)
    sales_name = quote.sales_user.get_full_name() or quote.sales_user.username
    authorized = getattr(django_settings, 'QUOTE_PDF_AUTHORIZED', 'Carlos Medina') or 'Carlos Medina'
    parsed = _parse_terms(quote.terms)
    payment_form = (getattr(django_settings, 'QUOTE_PDF_PAYMENT_FORM', '') or '') or parsed['payment']
    delivery_time = (getattr(django_settings, 'QUOTE_PDF_DELIVERY_TIME', '') or '') or parsed['delivery']
    warranty = (getattr(django_settings, 'QUOTE_PDF_WARRANTY', '') or '') or parsed['warranty']
    delivery_place = (getattr(django_settings, 'QUOTE_PDF_DELIVERY_PLACE', '') or '') or parsed['place']
    FOOTER_LEFT = COL_PARTIDA
    FOOTER_MID = 185
    FOOTER_RIGHT = 295
    FOOTER_RIGHT_END = TABLE_RIGHT
    pad_f = 10
    ROW1_H = 22
    ROW2_H = FOOTER_H - ROW1_H
    obs_pad = 10
    obs_labels_x = FOOTER_RIGHT + obs_pad
    obs_values_x = FOOTER_RIGHT + 112
    W_OBS_VAL = FOOTER_RIGHT_END - obs_values_x - obs_pad
    line_h = 7
    c.setLineWidth(0.5)
    footer_bottom = Y(FOOTER_Y + FOOTER_H)
    footer_top = Y(FOOTER_Y)
    c.line(FOOTER_LEFT, footer_bottom, FOOTER_LEFT, footer_top)
    c.line(FOOTER_MID, footer_bottom, FOOTER_MID, footer_top)
    c.line(FOOTER_RIGHT, footer_bottom, FOOTER_RIGHT, footer_top)
    c.line(FOOTER_RIGHT_END, footer_bottom, FOOTER_RIGHT_END, footer_top)
    row1_bottom = FOOTER_Y + ROW1_H
    c.line(FOOTER_LEFT, Y(row1_bottom), FOOTER_RIGHT_END, Y(row1_bottom))
    c.line(obs_values_x - 6, footer_bottom, obs_values_x - 6, Y(row1_bottom))
    c.line(FOOTER_LEFT, footer_bottom, FOOTER_RIGHT_END, footer_bottom)
    c.setFont(PDF_FONT_BODY, 7)
    y1 = FOOTER_Y + ROW1_H / 2 + 4
    y2_base = row1_bottom + 12
    W_LEFT = FOOTER_MID - FOOTER_LEFT - 85
    W_MID = FOOTER_RIGHT - FOOTER_MID - pad_f - 10
    c.drawString(FOOTER_LEFT + pad_f, Y(y1), 'Realizada por:')
    c.drawString(FOOTER_MID + pad_f, Y(y1), 'Autorizado:')
    c.setFont(PDF_FONT_BOLD, 7)
    c.drawString(obs_labels_x, Y(y1), 'Observaciones')
    c.setFont(PDF_FONT_BODY, 7)
    y2_center = row1_bottom + ROW2_H / 2 - 4
    c.drawString(FOOTER_LEFT + pad_f, Y(y2_center), _truncate_to_width(c, sales_name, W_LEFT))
    c.drawString(FOOTER_MID + pad_f, Y(y2_center), _truncate_to_width(c, authorized, W_MID))
    precios_en = 'USD' if moneda_display == 'USD' else 'Moneda nacional (MXN)'
    obs_items = [('Precios en:', _truncate_to_width(c, precios_en, W_OBS_VAL))]
    if moneda_display == 'MXN' and getattr(quote, 'usd_mxn_rate', None):
        obs_items.append(('Tipo de cambio:', _truncate_to_width(c, f'1 USD = {_fmt_money(quote.usd_mxn_rate)} MXN (lista en USD)', W_OBS_VAL)))
    obs_items.extend([('IVA', 'Precio más IVA'), ('Forma de Pago:', _truncate_to_width(c, payment_form, W_OBS_VAL) or ''), ('Tiempo de Entrega:', _truncate_to_width(c, delivery_time, W_OBS_VAL) or ''), ('Garantía:', _truncate_to_width(c, warranty, W_OBS_VAL) or ''), ('Lugar de entrega:', _truncate_to_width(c, delivery_place or 'Tienda', W_OBS_VAL) or 'Tienda')])
    for i, (label, value) in enumerate(obs_items):
        y_line = y2_base + i * line_h
        c.drawString(obs_labels_x, Y(y_line), label)
        c.drawString(obs_values_x, Y(y_line), value)
    notes_text = (quote.notes or '').strip()
    if notes_text and notes_text != 'SEED_QUOTES':
        notes_y = y2_base + 6 * line_h + 2
        obs_lines = _wrap_to_lines(c, notes_text, W_OBS_VAL, max_lines=2)
        for i, line in enumerate(obs_lines):
            c.drawString(obs_values_x, Y(notes_y + i * line_h), line)
    c.save()
    buf.seek(0)
    return buf.getvalue()
