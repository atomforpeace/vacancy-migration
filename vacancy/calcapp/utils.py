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

    rows = [
        'Время',
        'Температура',
        'nvd',
        'nvg',
        'nvt',
        'nv',
        'ns',
        'dl',
    ]

    # ws.row(0).width = 4000

    for col_num in range(len(rows)):
        ws.write(row_num, col_num, rows[col_num], font_style)

    font_style = xlwt.XFStyle()

    for row in data:
        row_num += 1

        # ws.row(row_num).width = 2000

        row = list(row.values())

        for col_num in range(len(rows)):
            if isinstance(row[col_num], list):
                row[col_num] = row[col_num][0]
            ws.write(row_num, col_num, row[col_num], font_style)

    # wb.save(response)
    wb.save(f'files/{filename}')

    # return FileResponse(f, as_attachment=True, filename='results.xlsx')
    return filename


def filter_results(results: list, excluded: list):
    for item in results:
        for excluded_item in excluded:
            item.pop(excluded_item, None)
    return results


def time_to_str(time_, delta_time):
    return f"{time_ + 1} - {time_ + delta_time}"
