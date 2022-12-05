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

    col_num = 0

    columns = [
        'Температура',
        'nvd',
        'nvg',
        'nvt',
        'nv',
        'Dcv',
    ]

    ws.col(0).width = 4000

    for row_num in range(len(columns)):
        ws.write(row_num, col_num, columns[row_num], font_style)

    font_style = xlwt.XFStyle()

    for col in data:
        col_num += 1

        ws.col(col_num).width = 2000

        col = list(col.values())

        for row_num in range(len(columns)):
            ws.write(row_num, col_num, col[row_num], font_style)

    # wb.save(response)
    wb.save(f'files/{filename}')

    # return FileResponse(f, as_attachment=True, filename='results.xlsx')
    return filename
