import xlwt
from io import StringIO, BytesIO
from datetime import datetime


from django.http import HttpResponse, FileResponse


# from mainapp.models import Course


def export_results_to_xls(data):
    # response = HttpResponse(content_type='application/ms-excel')
    f = BytesIO()

    now = datetime.now()

    filename = f'results_{now.strftime("%Y%m%d%H%M%S")}.xlsx'
    # response['Content-Disposition'] = f'attachment; filename={filename}'
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Результаты')

    font_style = xlwt.XFStyle()
    font_style.font.bold = True

    row_num = 0

    columns = [
        'Температура',
        'Dvt',
    ]

    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)

    font_style = xlwt.XFStyle()

    for row in data:
        row_num += 1

        row = list(row.values())

        for col_num in range(len(columns)):
            ws.write(row_num, col_num, str(row[col_num]), font_style)

    ws.col(0).width = 5000
    ws.col(1).width = 7000

    # wb.save(response)
    wb.save(f'files/{filename}')

    # return FileResponse(f, as_attachment=True, filename='results.xlsx')
    return filename
