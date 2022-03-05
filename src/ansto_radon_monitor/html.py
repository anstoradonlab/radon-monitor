

def status_as_html(title, info):
    """
    Produce a html table from a dictionary of status information
    
    title is a string,
    info is something like:

            info = {'var': ['LLD', "ULD", "HV", "InFlow", "ExFlow", "Airt", "RelHum", "Pres"],
                'description': ["Total Counts", "Noise Counts", "PMT Voltage", "Internal Flow Velocity", "External Flow Rate", "Air Temperature", "Relative Humidity", "Pressure" ],
                'units': ["Last 30 minutes", "Last 30 minutes", "V", "m/s", "L/min", "deg C", "%", "Pa"],
                'values': [1068, 13, .... (other values) ]
                }

    """
    html = ""
    html += f'<H1 class="instrument-name">{title}</H1>'
    html +=  '    <table class="dataframe" style="cellspacing="10" cellpadding="2">\n<tbody>'
    html +=  ("""<tr class="names">""" 
                  + "\n".join([
                  f"<td>{itm}</td>" for itm in info['description']])
                  + "\n</tr>\n")
    html +=  ("""<tr class="values">""" 
                  + "\n".join([
                  f"<td>{itm}</td>" for itm in info['values']])
                  + "\n</tr>\n")
    html +=  ("""<tr class="units">""" 
                  + "\n".join([
                  f"<td>{itm}</td>" for itm in info['units']])
                  + "\n</tr>\n")
    html +=  '</tbody>\n</table>\n'
    return html


def get_html_page(list_of_fragments):
    """Adds some suitable header/footer to a list of html fragments
        (as produced by status_as_html)"""
    
    template_head = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <title>template table</title>
    <style scoped>
        .dataframe{
            font-size:20px;
            font-family:Verdana, Geneva, Tahoma, sans-serif;
            border:none;
        }
        .dataframe tbody tr th:only-of-type {
            vertical-align: right;
            border:none;
        }
    
        .dataframe tbody tr th {
            vertical-align: top;
            border:none;
        }
    
        .dataframe thead th {
            text-align: right;
            border:none;
        }
        .dataframe small {
            font-size: 10px;
        }

        .dataframe td {
            width: 100px;
            height: 100px;
        }
        .names td {
            width: 100px;
            height: 20px;
            text-align: right;
            vertical-align: center;
            font-size: 15px;

        }

        .values td {
            width: 100px;
            height: 60px;
            text-align: right;
            vertical-align: center;
            font-size: 40px;

        }
        .units td {
            width: 100px;
            height: 20px;
            text-align: right;
            vertical-align: center;
            font-size: 15px;
        }

        .instrument-name h1{
            font-family:Verdana, Geneva, Tahoma, sans-serif;
            font-size: 20px;
        }
    </style>

    <style base>
        h1 {
            font-family:Verdana, Geneva, Tahoma, sans-serif;
            font-size: 20px;
        }

    </style>

</head>


<body class="base">"""
    template_footer = """
</body>
</html>"""
    html = template_head + '\n'.join(list_of_fragments) + template_footer
    return html