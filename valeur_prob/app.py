import dash
#import dash_auth

import dash_core_components as dcc
import dash_html_components as html
import flask
import os

from model import *
import update_pipeline

# Load Table
weights = {
            'Social' : 1.,
            'Transaction' : 2.,
            'Economy' : 1.,
            'Market Cap' : 4.,
            #'First Block' : 1.,
            'Activity Network' : 1.
          }
param_list = list(weights.keys())

table = model()
table.compute_sumproduct(weights)



server = flask.Flask(__name__)
server.secret_key = os.environ.get('secret_key', 'secret')
app = dash.Dash(__name__, server=server)
app.config.supress_callback_exceptions = True

# print(app.config)

# auth = dash_auth.BasicAuth(
#     app,
#     VALID_USERNAME_PASSWORD_PAIRS
# )


# Displaying
external_css = ["https://fonts.googleapis.com/css?family=Overpass:300,300i",
                "https://cdn.rawgit.com/plotly/dash-app-stylesheets/dab6f937fd5548cebf4c6dc7e93a10ac438f5efb/dash-technical-charting.css"]

for css in external_css:
    app.css.append_css({"external_url": css})

app.css.append_css({
    'external_url': (
        'https://cdn.rawgit.com/plotly/dash-app-stylesheets/8485c028c19c393e9ab85e1a4fafd78c489609c2/dash-docs-base.css',
        'https://cdn.rawgit.com/plotly/dash-app-stylesheets/30b641e2e89753b13e6557b9d65649f13ea7c64c/dash-docs-custom.css',
        'https://fonts.googleapis.com/css?family=Dosis'
    )
})

# Header

header = html.Div(
    className='header',
    children=html.Div(
        className='container-width',
        style={'height': '100%'},
        children=[
            html.A(html.Img(
                src="https://ledgys.io/assets/img/logo-test.png",
                className="logo"
            ), href='https://ledgys.io/', className="logo-link"),

            html.Div(className="links", children=[
                html.A('Valeur Probatoire', className="link active", href="/"),
                html.A('Variables', className="link", href="/variables"),
            ])
        ]
    )
)



app.layout = html.Div(children=
    [
    header, 
    html.H1(children='Ledgys Dashboard', 
        style={'text-align': 'center'}
        ),

    html.H3(children='Valeur probatoire'
        ),

    html.Hr(style={'margin': '0', 'margin-bottom': '5'}),

    dcc.Graph(id='val_prob_graph', 
            figure ={
            'data': [
                {'x': table.data.index, 'y': table.data.values, 'type': 'bar', 'name': 'SF'},
            ],
            'layout': {
                'title': 'Valeur Probatoire'
            }
        }),
    # Tabs
    html.Hr(style={'margin': '0', 'margin-bottom': '5'}),
    dcc.Tabs(
        tabs=[
            {'label': i, 'value': i} for i in param_list
        ],
        value=param_list[0],
        id='tabs'
    ),
    html.Div(id='tab_output')
    ],
    style={
        'width': '85%',
        'max-width': '1200',
        'margin-left': 'auto',
        'margin-right': 'auto',
        'font-family': 'overpass',
        'background-color': '#F3F3F3',
        'padding': '40',
        'padding-top': '20',
        'padding-bottom': '20',
    }
)




######## TABS #########
@app.callback(dash.dependencies.Output('tab_output', 'children'), 
    [dash.dependencies.Input('tabs', 'value')])
def display_content(value):
    return html.Div([
        dcc.Graph(
            id='graph',
            figure={
                'data': 
                [
                    {'x': i.df[value].index, 'y': table.df[value].values, 'type': 'bar', 'name': 'SF'},
                ],
                'layout': {
                }
            }
        ),
        html.Div("Explication de la variable")
    ])



if __name__ == '__main__':
    app.run_server(debug=True, threaded=True)