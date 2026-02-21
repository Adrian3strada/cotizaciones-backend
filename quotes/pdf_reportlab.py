"""
Genera el PDF completo de cotización con ReportLab.
Layout basado en Formato Cotización 2026.pdf.
Tamaño: A4 portrait (595 x 842 pts) - hoja normal.
Sistema: Y(y_from_top) = PAGE_H - y_from_top (sin invertir canvas).
"""
from decimal import Decimal
from io import BytesIO
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# A4 portrait: 595 x 842 pts (hoja normal vertical)
PAGE_W, PAGE_H = A4


def Y(y_from_top):
    """Convierte coordenada desde arriba (0=top) a ReportLab (0=bottom)."""
    return PAGE_H - y_from_top


def _img(c, path, x, y_bottom, w, h):
    if path and os.path.exists(path):
        c.drawImage(path, x, y_bottom, w, h, preserveAspectRatio=True, mask="auto")


def _truncate(s, max_len=45):
    s = str(s) if s else ""
    return s[:max_len] + "…" if len(s) > max_len else s


def _truncate_to_width(c, s, max_width, font="Helvetica", size=9):
    """Trunca el texto para que quepa en max_width pts."""
    s = str(s) if s else ""
    if not s:
        return s
    c.setFont(font, size)
    if c.stringWidth(s) <= max_width:
        return s
    ellipsis = "…"
    while len(s) > 1 and c.stringWidth(s[: len(s) - 1] + ellipsis) > max_width:
        s = s[:-1]
    return s[: len(s) - 1] + ellipsis if len(s) > 1 else ellipsis


def _fmt_money(val):
    if val is None:
        return "$0.00"
    v = Decimal(str(val))
    return f"${v:,.2f}"


def build_quote_pdf(quote, company, vigencia_texto, issue_date_formatted):
    """
    Genera el PDF completo de la cotización en memoria. Retorna bytes.
    Layout como Formato Cotización 2026.pdf (A4 portrait).
    """
    from django.contrib.staticfiles import finders
    from django.conf import settings as django_settings

    logo_path = finders.find("img/logo.png")
    hero_path = (
        finders.find("img/quote_header_right.png")
        or finders.find("img/quote_header_rigth.png")
    )

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))

    cust = quote.customer
    contact = quote.contact
    col_text = f"{cust.neighborhood or ''} {cust.city or ''}".strip()
    moneda_display = quote.currency or "MXN"

    M = 45  # margen
    LW = 120  # ancho logo

    # ==================== ENCABEZADO ====================
    # Logo izq
    _img(c, logo_path, M, Y(95), LW, 55)

    # Texto empresa (centro-arriba, como referencia)
    INFO_X = 195
    c.setFont("Helvetica-Bold", 10)
    c.drawString(INFO_X, Y(58), company.get("name", "Sistemas de Conteo de Personas."))
    c.setFont("Helvetica", 9)
    c.drawString(INFO_X, Y(68), company.get("street", "Blvd. Paseo de la República No. 13020 Int. 1307"))
    c.drawString(INFO_X, Y(78), f"{company.get('colony', '')} {company.get('postal_code', '')}".strip())
    c.drawString(INFO_X, Y(88), f"Tel: {company.get('phone', '')}")
    c.drawString(INFO_X, Y(98), f"RFC: {company.get('rfc', '')}")
    c.drawString(INFO_X, Y(108), f"e-mail: {company.get('email', '')}")
    c.setFont("Helvetica-Bold", 9)
    c.drawString(INFO_X, Y(118), company.get("website", "www.sisconper.com"))

# Caja Número / Fecha / Vigencia (pequeña)
    BOX_X, BOX_Y, BOX_W, BOX_H = M, 120, 135, 40
    c.setLineWidth(2)
    c.rect(BOX_X, Y(BOX_Y + BOX_H), BOX_W, BOX_H)

    # --- Layout interno (proporcional) ---
    pad_x = 8
    top_pad = 10          # espacio desde arriba
    line_gap = 14         # separación entre líneas

    y_num = BOX_Y + top_pad
    y_fecha = y_num + line_gap
    y_vig = y_fecha + line_gap

    # Etiquetas
    c.setFont("Helvetica-Bold", 9)   # <-- reduce fuente también
    c.drawString(BOX_X + pad_x, Y(y_num), "Número:")
    c.drawString(BOX_X + pad_x, Y(y_fecha), "Fecha:")
    c.drawString(BOX_X + pad_x, Y(y_vig), "Vigencia:")

    # Valores
    c.setFont("Helvetica", 9)
    value_x = BOX_X + 55  # <-- ajusta donde empiezan los valores (según ancho)
    c.drawString(value_x, Y(y_num), quote.quote_number)
    c.drawString(value_x, Y(y_fecha), issue_date_formatted)
    c.drawString(value_x, Y(y_vig), vigencia_texto)

    # Bloque CLIENTE + COTIZACIÓN (como imagen de referencia)
    CL_X, CL_Y, CL_W, CL_H = 195, 135, 215, 100
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
    # Línea de separación: arriba = contenido + Puesto, abajo = e-mail | Moneda
    BOTTOM_STRIP_H = 18
    LINE_Y = CL_Y + CL_H - BOTTOM_STRIP_H
    c.line(CL_X, Y(LINE_Y), CL_X + CL_W + COT_W, Y(LINE_Y))

    c.setFont("Helvetica-Bold", 11)
    c.drawString(CL_X, Y(CL_Y - 5), "CLIENTE")

    step = 10
    def _val(txt):
        return _truncate_to_width(c, txt, VAL_MAX_W)

    # --- FRANJA INFERIOR (debajo de la línea): e-mail | Moneda ---
    row_bottom = CL_Y + CL_H - 10
    c.setFont("Helvetica", 9)
    c.drawString(CL_X + 6, Y(row_bottom), "e-mail:")
    c.setFillColorRGB(0.05, 0.35, 0.85)
    c.drawString(VAL_X, Y(row_bottom), _val(contact.email if contact else ""))
    c.setFillColorRGB(0, 0, 0)
    c.drawString(COT_X + 8, Y(row_bottom), "Moneda")
    c.drawString(COT_X + 50, Y(row_bottom), moneda_display)

    # --- CONTENIDO: Contacto, Tels., C.P., Col., Calle, Web, Empresa, Puesto (arriba de la línea) ---
    row_start = CL_Y + 10
    c.drawString(CL_X + 6, Y(row_start), "Contacto:")
    c.setFont("Helvetica-Bold", 9)
    c.drawString(VAL_X, Y(row_start), _truncate_to_width(c, contact.full_name if contact else "", VAL_MAX_W, font="Helvetica-Bold"))
    c.setFont("Helvetica", 9)
    c.drawString(CL_X + 6, Y(row_start + step), "Tels.")
    tels = f"{cust.phone or ''} {cust.mobile or ''}".strip()
    c.drawString(VAL_X, Y(row_start + step), _val(tels))
    c.drawString(CL_X + 6, Y(row_start + step * 2), "C.P.")
    c.drawString(VAL_X, Y(row_start + step * 2), _val(cust.postal_code or ""))
    c.drawString(CL_X + 6, Y(row_start + step * 3), "Col.")
    c.drawString(VAL_X, Y(row_start + step * 3), _val(col_text))
    c.drawString(CL_X + 6, Y(row_start + step * 4), "Calle y No.")
    c.drawString(VAL_X, Y(row_start + step * 4), _val(cust.street_address or ""))
    c.drawString(CL_X + 6, Y(row_start + step * 5), "Web:")
    c.setFillColorRGB(0.05, 0.35, 0.85)
    c.drawString(VAL_X, Y(row_start + step * 5), _truncate_to_width(c, cust.website or "", VAL_MAX_W))
    c.setFillColorRGB(0, 0, 0)
    c.drawString(CL_X + 6, Y(row_start + step * 6), "Empresa:")
    c.setFont("Helvetica-Bold", 9)
    c.drawString(VAL_X, Y(row_start + step * 6), _truncate_to_width(c, cust.name, VAL_MAX_W, font="Helvetica-Bold"))
    c.setFont("Helvetica", 9)
    c.drawString(CL_X + 6, Y(row_start + step * 7), "Puesto:")
    c.drawString(VAL_X, Y(row_start + step * 7), _val(contact.position if contact else ""))

    # Cuadro COTIZACIÓN: título + nombre de la empresa cotizada
    cot_main = CL_Y + MONEDA_H + 12
    empresa_cotizada = _truncate_to_width(c, cust.name, COT_W - 16, font="Helvetica-Bold", size=12)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(COT_X + COT_W / 2, Y(cot_main), "COTIZACIÓN")
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(COT_X + COT_W / 2, Y(cot_main + 24), empresa_cotizada)

    # Imagen en esquina superior derecha del cuadro COTIZACIÓN (donde está la X)
    _img(c, hero_path, COT_X + COT_W - 68, Y(CL_Y + 6), 62, 62)

    # ==================== TABLA (ampliada, con líneas verticales) ====================
    TABLE_TOP = 255
    TABLE_LEFT = 40
    TABLE_RIGHT = PAGE_W - 30  # margen derecho 30 para ganar 10 pts
    # Bordes: Unidad(44), Cantidad(54), Desc(200) para que no se corte el texto
    COL_PARTIDA = TABLE_LEFT
    COL_PARTE = 78
    COL_DESC = 138
    COL_UNIT = 338
    COL_QTY = 382
    COL_PRICE_LEFT = 436
    COL_TOTAL_LEFT = 492
    COL_TOTAL_RIGHT = TABLE_RIGHT
    ROW_H = 24
    HEADER_Y = TABLE_TOP
    HEADER_H = 24
    pad = 6

    # Encabezado con fondo teal (truncar si no cabe para evitar solapamientos)
    c.setFillColor(colors.HexColor("#1F7A8C"))
    c.rect(COL_PARTIDA, Y(HEADER_Y + HEADER_H), TABLE_RIGHT - COL_PARTIDA, HEADER_H, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    header_text_y = HEADER_Y + 10
    pad = 6
    c.drawCentredString(COL_PARTIDA + (COL_PARTE - COL_PARTIDA)/2, Y(header_text_y), _truncate_to_width(c, "Partida", COL_PARTE - COL_PARTIDA - pad, font="Helvetica-Bold"))
    c.drawString(COL_PARTE + pad, Y(header_text_y), _truncate_to_width(c, "No de parte", COL_DESC - COL_PARTE - pad, font="Helvetica-Bold"))
    c.drawString(COL_DESC + pad, Y(header_text_y), _truncate_to_width(c, "Descripción", COL_UNIT - COL_DESC - pad, font="Helvetica-Bold"))
    c.drawCentredString(COL_UNIT + (COL_QTY - COL_UNIT)/2, Y(header_text_y), _truncate_to_width(c, "Unidad", COL_QTY - COL_UNIT - pad, font="Helvetica-Bold"))
    c.drawCentredString(COL_QTY + (COL_PRICE_LEFT - COL_QTY)/2, Y(header_text_y), _truncate_to_width(c, "Cantidad", COL_PRICE_LEFT - COL_QTY - pad, font="Helvetica-Bold"))
    c.drawCentredString(COL_PRICE_LEFT + (COL_TOTAL_LEFT - COL_PRICE_LEFT)/2, Y(header_text_y), _truncate_to_width(c, "Precio Unit.", COL_TOTAL_LEFT - COL_PRICE_LEFT - pad, font="Helvetica-Bold"))
    c.drawCentredString(COL_TOTAL_LEFT + (COL_TOTAL_RIGHT - COL_TOTAL_LEFT)/2, Y(header_text_y), _truncate_to_width(c, "Total", COL_TOTAL_RIGHT - COL_TOTAL_LEFT - pad, font="Helvetica-Bold"))
    c.setFillColor(colors.black)

    # Agrupar items por group_name
    items = list(quote.items.select_related("camera_model").order_by("id"))
    groups = []
    current_group = None
    for item in items:
        gn = (item.group_name or "").strip()
        if gn:
            if current_group is None or current_group[0] != gn:
                current_group = [gn, []]
                groups.append(current_group)
            current_group[1].append(item)
        else:
            current_group = None
            groups.append([None, [item]])

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

    for group_name, group_items in groups:
        if group_name:
            # Fila de grupo (sin línea debajo)
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(COL_PARTIDA + W_PARTIDA/2, Y(y_row), _truncate_to_width(c, str(partida), W_PARTIDA))
            c.drawString(COL_DESC + pad, Y(y_row), _truncate_to_width(c, group_name, W_DESC))
            y_row += ROW_H
            for i, item in enumerate(sorted(group_items, key=lambda x: (x.order_in_group, x.id))):
                cam = item.camera_model
                desc = cam.name or cam.model_code
                unidad = "Pza." if "cámara" in desc.lower() or "camera" in desc.lower() else "Serv."
                sub_partida = f"{partida}.{i + 1}"
                c.setFont("Helvetica", 8)
                c.drawCentredString(COL_PARTIDA + W_PARTIDA/2, Y(y_row), _truncate_to_width(c, sub_partida, W_PARTIDA))
                c.drawString(COL_PARTE + pad, Y(y_row), _truncate_to_width(c, cam.model_code, W_PARTE))
                c.drawString(COL_DESC + pad, Y(y_row), _truncate_to_width(c, desc, W_DESC))
                c.drawCentredString(COL_UNIT + W_UNIT/2, Y(y_row), _truncate_to_width(c, unidad, W_UNIT))
                c.drawCentredString(COL_QTY + W_QTY/2, Y(y_row), _truncate_to_width(c, str(item.quantity), W_QTY))
                c.drawRightString(COL_TOTAL_LEFT - pad, Y(y_row), _truncate_to_width(c, _fmt_money(item.unit_price), W_PRICE))
                c.drawRightString(COL_TOTAL_RIGHT - pad, Y(y_row), _truncate_to_width(c, _fmt_money(item.line_subtotal), W_TOTAL))
                y_row += ROW_H
            partida += 1
        else:
            # Items sin grupo (filas planas)
            for item in group_items:
                cam = item.camera_model
                desc = cam.name or cam.model_code
                unidad = "Pza." if "cámara" in desc.lower() or "camera" in desc.lower() else "Serv."
                c.setFont("Helvetica", 8)
                c.drawCentredString(COL_PARTIDA + W_PARTIDA/2, Y(y_row), _truncate_to_width(c, str(partida), W_PARTIDA))
                c.drawString(COL_PARTE + pad, Y(y_row), _truncate_to_width(c, cam.model_code, W_PARTE))
                c.drawString(COL_DESC + pad, Y(y_row), _truncate_to_width(c, desc, W_DESC))
                c.drawCentredString(COL_UNIT + W_UNIT/2, Y(y_row), _truncate_to_width(c, unidad, W_UNIT))
                c.drawCentredString(COL_QTY + W_QTY/2, Y(y_row), _truncate_to_width(c, str(item.quantity), W_QTY))
                c.drawRightString(COL_TOTAL_LEFT - pad, Y(y_row), _truncate_to_width(c, _fmt_money(item.unit_price), W_PRICE))
                c.drawRightString(COL_TOTAL_RIGHT - pad, Y(y_row), _truncate_to_width(c, _fmt_money(item.line_subtotal), W_TOTAL))
                y_row += ROW_H
                partida += 1

    disc = quote.special_discount_amount or Decimal("0")
    if disc != 0:
        pct = quote.special_discount_percent or 0
        c.setFont("Helvetica-Bold", 8)
        c.drawString(COL_DESC + pad, Y(y_row), _truncate_to_width(c, "Descuento", W_DESC))
        c.drawCentredString(COL_UNIT + W_UNIT/2, Y(y_row), "Desc.")
        c.drawCentredString(COL_QTY + W_QTY/2, Y(y_row), "1")
        c.drawRightString(COL_TOTAL_LEFT - pad, Y(y_row), _truncate_to_width(c, f"{pct}%", W_PRICE))
        c.drawRightString(COL_TOTAL_RIGHT - pad, Y(y_row), _truncate_to_width(c, f"-{_fmt_money(disc)}", W_TOTAL))
        y_row += ROW_H

    if optional_rows:
        y_row += 5
        c.setFont("Helvetica-Bold", 8)
        c.drawString(COL_DESC + pad, Y(y_row), "Opcional")
        y_row += ROW_H

    for opt in optional_rows:
        c.setFont("Helvetica", 8)
        c.drawCentredString(COL_PARTIDA + W_PARTIDA/2, Y(y_row), _truncate_to_width(c, str(opt.get("partida", partida)), W_PARTIDA))
        c.drawString(COL_PARTE + pad, Y(y_row), _truncate_to_width(c, "—", W_PARTE))
        c.drawString(COL_DESC + pad, Y(y_row), _truncate_to_width(c, opt.get("desc", ""), W_DESC))
        c.drawCentredString(COL_UNIT + W_UNIT/2, Y(y_row), _truncate_to_width(c, "Serv.", W_UNIT))
        c.drawCentredString(COL_QTY + W_QTY/2, Y(y_row), _truncate_to_width(c, "1", W_QTY))
        c.drawRightString(COL_TOTAL_LEFT - pad, Y(y_row), _truncate_to_width(c, _fmt_money(opt.get("monto")), W_PRICE))
        c.setFont("Helvetica-Bold", 8)
        c.drawRightString(COL_TOTAL_RIGHT - pad, Y(y_row), _truncate_to_width(c, _fmt_money(opt.get("monto")) + " MX", W_TOTAL))
        y_row += ROW_H

    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(COL_PRICE_LEFT + W_PRICE/2, Y(y_row + 8), "Total")
    c.drawRightString(COL_TOTAL_RIGHT - pad, Y(y_row + 8), _truncate_to_width(c, _fmt_money(quote.total) + " MX", W_TOTAL))
    y_row += ROW_H + 16

    # La tabla de partidas se extiende hasta el pie de página
    BOTTOM_MARGIN = 60  # margen inferior mínimo (pts desde el borde)
    FOOTER_Y = 680
    FOOTER_H = PAGE_H - FOOTER_Y - BOTTOM_MARGIN  # 842-680-60 = 102, pero limitamos a 100
    FOOTER_H = min(FOOTER_H, 100)
    TABLE_BOTTOM = FOOTER_Y
    table_bottom_y = TABLE_BOTTOM

    # Líneas verticales de separación entre columnas + bordes de tabla (hasta el pie)
    c.setLineWidth(0.5)
    tbl_bottom = Y(table_bottom_y)
    tbl_top = Y(HEADER_Y + HEADER_H)
    for col_x in (COL_PARTIDA, COL_PARTE, COL_DESC, COL_UNIT, COL_QTY, COL_PRICE_LEFT, COL_TOTAL_LEFT, COL_TOTAL_RIGHT):
        c.line(col_x, tbl_bottom, col_x, tbl_top)
    # Línea horizontal inferior de la tabla
    c.line(COL_PARTIDA, tbl_bottom, COL_TOTAL_RIGHT, tbl_bottom)

    # ==================== PIE (apartados en celdas) ====================
    sales_name = quote.sales_user.get_full_name() or quote.sales_user.username
    authorized = getattr(django_settings, "QUOTE_PDF_AUTHORIZED", "") or ""

    # Celdas del pie: 3 columnas bien proporcionadas (alineadas con la tabla)
    FOOTER_LEFT = COL_PARTIDA
    FOOTER_MID = 210
    FOOTER_RIGHT = 370
    FOOTER_RIGHT_END = TABLE_RIGHT
    CELL_H = FOOTER_H / 6  # 6 filas, altura uniforme sin pasarse
    pad_f = 8

    # Dibujar celdas del pie
    c.setLineWidth(0.5)
    footer_bottom = Y(FOOTER_Y + FOOTER_H)
    footer_top = Y(FOOTER_Y)

    # Líneas verticales entre columnas
    c.line(FOOTER_LEFT, footer_bottom, FOOTER_LEFT, footer_top)
    c.line(FOOTER_MID, footer_bottom, FOOTER_MID, footer_top)
    c.line(FOOTER_RIGHT, footer_bottom, FOOTER_RIGHT, footer_top)
    c.line(FOOTER_RIGHT_END, footer_bottom, FOOTER_RIGHT_END, footer_top)

    # Líneas horizontales entre filas (6 filas)
    for i in range(1, 6):
        y_cell = FOOTER_Y + i * CELL_H
        c.line(FOOTER_LEFT, Y(y_cell), FOOTER_RIGHT_END, Y(y_cell))
    # Línea inferior del pie (cierra el recuadro sin pasarse)
    c.line(FOOTER_LEFT, footer_bottom, FOOTER_RIGHT_END, footer_bottom)

    # Contenido en celdas (centrado verticalmente)
    def _cell_y(row):
        return Y(FOOTER_Y + (row - 0.5) * CELL_H + 5)

    c.setFont("Helvetica", 9)

    # Fila 1: Realizada por | Autorizado | Observaciones
    c.drawString(FOOTER_LEFT + pad_f, _cell_y(1), "Realizada por:")
    c.drawString(FOOTER_LEFT + 78, _cell_y(1), _truncate(sales_name, 20))
    c.drawString(FOOTER_MID + pad_f, _cell_y(1), "Autorizado:")
    c.drawString(FOOTER_MID + 72, _cell_y(1), _truncate(authorized, 20))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(FOOTER_RIGHT + pad_f, _cell_y(1), "Observaciones")
    c.setFont("Helvetica", 9)
    if quote.notes:
        c.drawString(FOOTER_RIGHT + pad_f, _cell_y(2), _truncate(quote.notes, 40))

    # Fila 2: Precios en | IVA
    c.drawString(FOOTER_LEFT + pad_f, _cell_y(2), "Precios en:")
    c.drawString(FOOTER_LEFT + 58, _cell_y(2), "Moneda nacional" + (" /USD" if moneda_display == "USD" else ""))
    c.drawString(FOOTER_MID + pad_f, _cell_y(2), "IVA Precio más IVA")

    # Filas 3-6: Forma de Pago, Tiempo de Entrega, Garantía, Lugar de entrega
    c.drawString(FOOTER_LEFT + pad_f, _cell_y(3), "Forma de Pago:")
    c.drawString(FOOTER_LEFT + pad_f, _cell_y(4), "Tiempo de Entrega:")
    c.drawString(FOOTER_LEFT + pad_f, _cell_y(5), "Garantía:")
    c.drawString(FOOTER_MID + pad_f, _cell_y(3), "Lugar de entrega:")

    c.save()
    buf.seek(0)
    return buf.getvalue()
