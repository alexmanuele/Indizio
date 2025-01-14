import itertools as it
import sys
from tempfile import NamedTemporaryFile

import numpy as np
import pandas as pd

import dash
from dash.dependencies import Output, Input, State
from dash import dcc, dash_table, html, ALL

import dash_bootstrap_components as dbc
import dash_cytoscape as cyto

# Load extra layouts
cyto.load_extra_layouts()

import networkx as nx

import plotly.graph_objects as go
import plotly.express as px

from components import *
from utils import *

if __name__ == '__main__':

    FONT_AWESOME = "https://use.fontawesome.com/releases/v5.7.2/css/all.css"
    external_stylesheets = [FONT_AWESOME, dbc.themes.JOURNAL,]
    app = dash.Dash(__name__, external_stylesheets=external_stylesheets,suppress_callback_exceptions=True)
    server = app.server
    colorscales=px.colors.named_colorscales()
    try:
        assert len(sys.argv) == 2
    except:
        raise ValueError('app.py accepts exactly one argument. Please use the included sample sheet maker to create the required file.')
    #get the files
    print("Parsing sample sheet. . .")
    metas, dms, pa, tree = initialize_data(sys.argv[1])
    #make the network
    print("Initializing network. . . ")
    G = make_graph(metas, dms)
    node_items = [{'label': node, 'value': node} for node in G.nodes]
    print("Done. Configuring dashboard. . .")
    dm_metric_options = []

    for i, tup in enumerate(dms):
        dm_metric_options.append({
            'label': tup[0],
            'value': tup[0]
        })
    #dms is a list of tuples
    dm_dict = {attr:frame for attr, frame in dms}
    #metas is either list of tuples or empty list
    meta_dict = {attr:frame for attr,frame in metas}
    default_stylesheet = [
                            {
                                'selector':'edge',
                                'style': {
                                    #'width': 'mapData(lr, 50, 200, 0.75, 5)',
                                    'opacity': 0.4,
                                },
                            },
                            {'selector': 'node',
                                'style':{
                                    #'color': '#317b75',
                                    'background-color': '#317b75',
                                    'content': 'data(label)',
                                },
                            },
                            {
                                'selector': '.focal',
                                'style':{
                                    #'color': '#E65340',
                                    'background-color': '#E65340',
                                    'content': 'data(label)',
                                },
                            },
                            {'selector': '.other',
                                'style':{
                                    #'color': '#317b75',
                                    'background-color': '#317b75',
                                    'content': 'data(label)',
                                },
                            },
                            ]



    ################################################################################
    ### Page Layouts                                                             ###
    ################################################################################

    ### Entry Point. Also Serves as data dump for sharing between apps  ###
    app.layout = html.Div([
        dcc.Location(id='url', refresh=False),
        #Stores for data persistence.
        dcc.Store(id='graph-store'),

        make_navbar(active=0),
        html.Div(id='page-content'),
    ])

    ### Landing Page ###
    #Adapted from https://getbootstrap.com/docs/4.0/examples/product/
    landing_page_layout = [
        html.Div(className="position-relative overflow-hidden p-3 p-md-5 m-md-3 text-center bg-light",children=[
            html.Div(className="col-md-5 p-lg-5 mx-auto my-5", children=[
                html.H1('Indizio', className="display-4 font-weight-normal"),
                html.P("Interactively explore connected data.", className='lead font-weight-normal'),
                html.P("(Note: This page will be replaced by a data upload form later.)", className='lead font-weight-normal'),
                html.A('Get Started', href='page-1', className='btn btn-outline-secondary'),
            ])
        ]),
        html.Div(className="d-md-flex flex-md-equal w-100 my-md-3 pl-md-3",children=[
            html.Div(className="bg-dark mr-md-3 pt-3 px-3 pt-md-5 px-md-5 text-center text-white overflow-hidden",children=[
                html.Div(className="my-3 py-3", children=[
                    html.H2('Heatmap viewer.', className='display-5'),
                    html.P(children=["View connected data as heatmaps. Explroe heatmaps for each distance metric you uploaded. Click 'Matrices'.",
                                     ], className='lead'),
                ])
            ]),
            html.Div(className="bg-light mr-md-3 pt-3 px-3 pt-md-5 px-md-5 text-center overflow-hidden",children=[
                html.Div(className="my-3 py-3", children=[
                    html.H2("Explore Specific Subnetworks.", className="display-5"),
                    html.P('Visualize networks surrounding specific nodes. Choose your node or nodes, select filtering parameters, and explore. Click "Network Visualisation."', className='lead'),

                ])
            ])
        ]),
        html.Div(className="d-md-flex flex-md-equal w-100 my-md-3 pl-md-3",children=[
            html.Div(className="bg-light mr-md-3 pt-3 px-3 pt-md-5 px-md-5 text-center overflow-hidden",children=[
                html.Div(className="my-3 py-3", children=[
                    html.H2('View Macro Level Statistics.', className='display-5'),
                    html.P("View at a macro level how LR and p value choices influence network properties. Click 'Network Statistics'.", className='lead'),
                ])
            ]),
            html.Div(className="bg-primary mr-md-3 pt-3 px-3 pt-md-5 px-md-5 text-center text-white overflow-hidden",children=[
                html.Div(className="my-3 py-3", children=[
                    html.H2("(Not yet) View genome presence/absence cladogram.", className="display-5"),
                    html.P('See the presence and absence of genes etc. in a per genome basis. (Not yet implemented).', className='lead'),

                ])
            ])
        ]),
    ]

    ### Heat Map Viewer Layout ###
    page1_layout = dbc.Container(fluid=True, children=[
        dbc.Row(id='heatmap-display',children=[
            dbc.Col([
                dcc.Loading(dcc.Graph(id='heatmap-graph'),),
            ],className='col-9'),

            dbc.Col(
                [
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            dbc.Label("Choose Metric"),
                            dcc.Dropdown(
                                id="dataset-select", value=dm_metric_options[0]['value'],
                                options=dm_metric_options,
                            ),
                    ],className='pl-5 pr-5'),
                        ],),
                    ]),
                    dbc.Row([
                    html.P("Color Scale"),
                    dcc.Dropdown(
                        id='colorscale',
                        options=[{"value": x, "label": x}
                                 for x in colorscales],
                        value='inferno'
                    ),]),
                    dbc.RadioItems(
                        options=[
                            {"label": "Continuous", "value": 1},
                            {"label": "Binned", "value": 2},
                        ],
                        value=1,
                        id="plot-mode-radio", inline=True,
                    ),
                    dbc.Row([
                        dbc.Button(html.Span([html.I(className="fas fa-minus-circle ml-2")]), className='col col-1',id='minus-button' ),
                        dbc.Button(html.Span([html.I(className="fas fa-plus-circle ml-2")]), className='col col-1', id='plus-button'),
                        dbc.Col(id='slider-container',
                            children=[
                                dcc.RangeSlider(min=0,max=0)
                            ]
                        ),
                    ]),
                    dbc.Button('Update Heatmap', id='heatmap-button', color='secondary'),
                ]
            ),
        ])
    ])


    ### Network viz layout ###
    page2_layout = dbc.Container(fluid=True, children=[
        dbc.Row([
            dbc.Row([
                html.H3(children="Network Visualization"),
                dbc.Col(children=[
                    dbc.Row(children=[
                        html.Div([
                            dbc.Label("Change network Layout"),
                            dcc.Dropdown(
                                id='network-callbacks-1',
                                value='grid',
                                clearable=False,
                                options=[
                                    {'label': name.capitalize(), 'value': name}
                                    #for name in ['grid', 'random', 'circle', 'cose', 'concentric', 'breadthfirst']
                                    for name in [
                                        'random',
                                        'grid',
                                        'circle',
                                        'concentric',
                                        'breadthfirst',
                                        'cose',
                                        'cose-bilkent',
                                        'cola',
                                        'klay',
                                        'spread',
                                        'euler'
                                    ]
                                ], className="bg-light text-dark",
                            ),
                            ]),
                        html.Div([
                            dbc.Col([
                                dbc.Label('Select a node of interest.'),
                                dcc.Dropdown(
                                    id='node-dropdown',
                                    options=node_items,
                                    value=[],
                                    className="bg-light text-dark",
                                    multi=True),

                            ]),

                            dbc.Col(make_network_form(dm_dict.keys())),
                        ]),

                        html.Div([dbc.Button('Update Network', id='interactive-button', color='success', style={'margin-bottom': '1em'},)],className="d-grid gap-2"),
                        html.Div([dbc.Button('Download as GraphML', id='download-network-button', color='success', style={'margin-bottom': '1em'},), dcc.Download(id='download-network')],className="d-grid gap-2"),

                    ]),

                    dbc.Row(

                            children=dbc.Card(
                                [
                                    dbc.CardHeader("Network Properties", className="bg-primary text-white"),
                                    dbc.CardBody(
                                        html.P("Lorem Ipsum and all that.", className='card-text text-dark',
                                        id='node-selected')
                                    )
                                ]
                            )
                    ),
                ]),
                dbc.Col(children=[
                    #dbc.Col(dcc.Graph(id='interactive-graph')),  # Not including fig here because it will be generated with the callback
                    dbc.Col(cyto.Cytoscape(
                        id='network-plot',
                        elements=[],
                        stylesheet=default_stylesheet,
                        style={'width': '100%', 'height': '800px'},
                        layout={
                            'name': 'grid'
                        },
                    ),className='bg-white'),

                ], className='col col-xl-9 col-lg-8 col-md-6 '),
            ], className='bg-secondary text-white')
        ]),
    ])

    page3_layout = dbc.Container(fluid=True, children=[
        dbc.Row(id='historgram-display',children=[
            dbc.Col([
                dcc.Loading(dcc.Graph(id='histogram-graph'),),
                dbc.Row([
                    dbc.Col([
                        html.Div([
                        dbc.Row([
                            dbc.Col([
                                html.Div([
                                    dbc.Label("Choose Metric"),
                                    dcc.Dropdown(
                                        id="histogram-metric-select", value=dm_metric_options[0]['value'],
                                        options=dm_metric_options,
                                    ),
                            ],className='pl-5 pr-5'),
                                ],),
                            ]),
                            html.Div([dbc.Button('Re-calculate Plot', id='histogram-button', color='primary', style={'margin-bottom': '1em'})],className="d-grid gap-2"),
                        ]),
                    ],className='pl-5 pr-5'),
                ],),
            ]),
        ]),
    ])



    ################################################################################
    ### Heatmap Callbacks                                                        ###
    ################################################################################
    @app.callback(
        Output('slider-container', 'children'),
        [Input('dataset-select', 'value')]
    )
    def update_colorscale_slider(metric):
        df = dm_dict[metric]
        maxval = np.nanmax(df.values)
        minval = np.nanmin(df.values)
        slider = dcc.RangeSlider(min=minval, max=maxval,
                                 step=(maxval - minval)/100,
                                 marks= {
                                            minval: {'label': '{:.2f}'.format(minval)},
                                            maxval: {'label': '{:.2f}'.format(maxval),}
                                         },
                                 value=[minval, maxval],
                                 tooltip={"placement": "bottom", "always_visible": False},
                                 id={'role': 'slider', 'index':0})
        print(minval, maxval)
        return slider

    @app.callback(
    Output({"role" : "slider", "index": ALL}, 'value'),
    [Input('minus-button', 'n_clicks'),
     Input('plus-button', 'n_clicks'),
     State({"role" : "slider", "index": ALL}, 'value'),]
    )
    def update_marks(minus, plus, sliderstate):
        ctx = dash.callback_context
        slidervals = sliderstate[0]
        minval = slidervals[0]
        maxval = slidervals[-1]
        n_vals = len(slidervals)
        if not ctx.triggered:
            button_id = 'noclick'
        else:
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if button_id == 'noclick':
            return dash.no_update
        elif button_id == 'minus-button':
            if n_vals <= 2:
                return dash.no_update
            vals = list(np.linspace(minval, maxval, n_vals-1))
            return [vals]
        else:
            vals = list(np.linspace(minval, maxval, n_vals+1))
            return [vals]

    @app.callback(
        Output('heatmap-graph', 'figure'),
        [Input('heatmap-button', 'n_clicks'),
         State('dataset-select', 'value'),
         State('colorscale', 'value'),
         State('plot-mode-radio', "value"),
         State({'role': 'slider', 'index': ALL}, 'value')]
    )
    def plot(click, dataset, scale, mode, slidervals):

        fig = go.Figure()
        #empty initially

        feature_df = dm_dict[dataset]
        meta_df = None

        if dataset in meta_dict.keys():
            meta_df = meta_dict[dataset]
        if len(slidervals) == 0:
            slidervals = [np.nanmin(feature_df.values), np.nanmax(feature_df.values)]
        else:
            slidervals = slidervals[0]
        slidervals = sorted(slidervals)
        if mode == 2:
            colorscale = []
            colors = get_color(scale, np.linspace(0,1, len(slidervals)-1))
            minval = min(slidervals)
            maxval = max(slidervals)
            normed_vals = [(x-minval)/(maxval-minval) for x in slidervals]
            for i, _ in enumerate(normed_vals[:-1]):
                colorscale.append([normed_vals[i], colors[i]])
                colorscale.append([normed_vals[i+1], colors[i]])
        else:
            colorscale = scale

        ava_hm = go.Heatmap(x=feature_df.columns,
                            y=feature_df.index,
                            z=feature_df,
                            colorscale=colorscale,
                            zmin=slidervals[0],
                            zmax=slidervals[-1],
                            #colorbar=colorbar,
                           )
        if type(meta_df) != type(None):
            meta_hm = go.Heatmap(x=meta_df.columns,
                                 y=meta_df.index,
                                 z=meta_df,
                                 colorscale=colorscale,
                                 zmin=slidervals[0],
                                 zmax=slidervals[-1],
                                 showscale=False
            )
            f1 = go.Figure(meta_hm)
            for data in f1.data:
                fig.add_trace(data)

            f2 = go.Figure(ava_hm)
            for i in range(len(f2['data'])):
                f2['data'][i]['xaxis'] = 'x2'

            for data in f2.data:
                fig.add_trace(data)

            fig.update_layout({'height':800})
            fig.update_layout(xaxis={'domain': [.0, .20],
                                              'mirror': False,
                                              'showgrid': False,
                                              'showline': False,
                                              'zeroline': False,
                                              #'ticks':"",
                                              #'showticklabels': False
                                    })
            # Edit xaxis2
            fig.update_layout(xaxis2={'domain': [0.25, 1.0],
                                               'mirror': False,
                                               'showgrid': False,
                                               'showline': False,
                                               'zeroline': False,
                                               #'showticklabels': False,
                                               #'ticks':""
                                     })
        else:
            f = go.Figure(ava_hm)
            for data in f.data:
                fig.add_trace(data)
            fig.update_layout({'height':800})
            fig.update_layout(xaxis={'mirror': False,
                                     'showgrid': False,
                                     'showline': False,
                                     'zeroline': False,
                                     'tickmode': 'array',
                                     'ticktext': feature_df.columns.str.slice(-8).tolist()})
        return fig

    ################################################################################
    ### Network Visualization Callbacks                                          ###
    ################################################################################
    @app.callback(
        Output('network-plot', 'layout'),
        Input('network-callbacks-1', 'value')
        )
    def update_layout(layout):
        return {
            'name': layout,
            'animate': True
        }
    @app.callback(
        Output("download-network", "data"),
        [Input('download-network-button', 'n_clicks'),
        State('node-dropdown', 'value'),
        State('degree', 'value'),
        State({'role': 'threshold', 'index': ALL}, 'value'),
        State({'role': 'bounds-select', 'index': ALL}, 'value'),
        ]
    )
    def download_network(click, nodes, degree, thresholds, bounds):
        n_nodes = 0
        n_edges = 0
        attributes = list(dm_dict.keys())
        H=None
        if len(nodes) == 0:
            elements = []
        else:
            H = filter_graph(G, nodes, degree, attributes, thresholds, bounds)
        if H:
            nfile = NamedTemporaryFile('w')
            #nfile.name = 'tmp/network.graphml' TODO how can i change the name of this file?
            nx.readwrite.graphml.write_graphml(H, nfile.name)
            return dcc.send_file(nfile.name)
        return dash.no_update
    @app.callback(
        Output('network-plot', 'elements'),
        Output('node-selected', 'children'),
        [Input('interactive-button', 'n_clicks'),
         State('node-dropdown', 'value'),
         State('degree', 'value'),
         State({'role': 'threshold', 'index': ALL}, 'value'),
         State({'role': 'bounds-select', 'index': ALL}, 'value'),]
    )
    def update_elements(click, nodes, degree, thresholds, bounds):
        n_nodes = 0
        n_edges = 0
        attributes = list(dm_dict.keys())
        if len(nodes) == 0:
            nodes = [i['value'] for i in node_items]
        #else:
        H = filter_graph(G, nodes, degree, attributes, thresholds, bounds)
        # Graph basics
        elements = nx_to_dash(H, nodes)
        n_nodes = len(H.nodes)
        n_edges = len(H.edges)
        #end else
        summary_data = [
            dbc.ListGroupItem("Focal Node: {}".format(nodes)),
            dbc.ListGroupItem("Degree: {}".format(degree)),
        ]
        for attr, thresh in zip(attributes, thresholds):
            summary_data.append(
                dbc.ListGroupItem("{0} threshold: {1}".format(attr, thresh)),
            )
        summary_data += [dbc.ListGroupItem("n Nodes: {}".format(n_nodes)),
                         dbc.ListGroupItem("n Edges: {}".format(n_edges)),]
        #summary = html.P("Focal Node: {0}\nDegree: {1}<br>LR Threshold: {2}<br>P Threshold: {3}<br>Nodes in selection: {4}<br>Edges in selection: {5}".format(node, degree, lr_threshold, p_threshold,n_nodes, n_edges))
        summary = dbc.ListGroup(
            summary_data,
        )
        return elements, summary

    @app.callback(Output('network-plot', 'stylesheet'),
                [Input('network-plot', 'tapNode')])
    def highlight_edges(node):
        if not node:
            return default_stylesheet

        stylesheet = [
                            {
                                'selector':'edge',
                                'style': {
                                    'opacity': 0.4,
                                    #'width': 'mapData(lr, 50, 200, 0.75, 5)',
                                },
                            },
                            {'selector': 'node',
                                'style':{
                                    #'color': '#317b75',
                                    'background-color': '#317b75',
                                    'content': 'data(label)',
                                    'width': 'mapData(degree, 1, 100, 25, 200)'
                                },
                            },
                            {
                                'selector': '.focal',
                                'style':{
                                    #'color': '#E65340',
                                    'background-color': '#E65340',
                                    'content': 'data(label)',
                                },
                            },
                            {'selector': '.other',
                                'style':{
                                    #'color': '#317b75',
                                    'background-color': '#317b75',
                                    'content': 'data(label)',
                                },
                            },
                            {
                                "selector": 'node[id = "{}"]'.format(node['data']['id']),
                                "style": {
                                    'background-color': '#B10DC9',
                                    "border-color": "purple",
                                    "border-width": 2,
                                    "border-opacity": 1,
                                    "opacity": 1,

                                    "label": "data(label)",
                                    "color": "#B10DC9",
                                    "text-opacity": 1,
                                    "font-size": 12,
                                    'z-index': 9999
                                }
                            }
                        ]
        for edge in node['edgesData']:
            stylesheet.append({
                'selector': 'node[id= "{}"]'.format(edge['target']),
                'style': {
                    'background-color': 'blue',
                    'opacity': 0.9,

                }
            })
            stylesheet.append({
                'selector': 'node[id= "{}"]'.format(edge['source']),
                'style': {
                    'background-color': 'blue',
                    'opacity': 0.9,

                }
            })
            stylesheet.append({
                "selector": 'edge[id= "{}"]'.format(edge['id']),
                "style": {
                    "line-color": 'green',
                    'opacity': 0.9,
                    'z-index': 5000
                }
            })
        return stylesheet

    ################################################################################
    ### Network Visualization Callbacks                                          ###
    ################################################################################
    @app.callback(
        Output('histogram-graph', 'figure'),
        [Input('histogram-button', 'n_clicks'),
        State('histogram-metric-select', 'value'),
        State('histogram-y-select', 'value')]
    )
    def show_histogram(click, metric_sel, y_sel):
        metric_map = {
                        '1': ('lr', 'p'),
                        '2': ('p', 'lr')
                    }
        y_map = {
                    '1': 'node_degree',
                    '2': 'n_nodes',
                    '3': 'n_edges'
                }
        dynamic_metric, static_metric = metric_map[str(metric_sel)]
        y = y_map[str(y_sel)]


        lte = lambda x,y: x<=y
        gte = lambda x,y: x>=y

        if dynamic_metric == 'lr':
            search = [25, 50, 100, 150]
            dfun = gte
            sfun = lte

        else:
            search = [0.05, 1e-5, 1e-9, 1e-12]
            dfun = lte
            sfun = gte

        if static_metric == 'p':
            static_threshold = 0.05
        else:
            static_threshold = 50

        records = []
        node_list = []
        for node in G.nodes:
            node_list.append((node, {**G.nodes[node]}))

        for dynamic_threshold in search:
            F= nx.Graph()
            F.add_nodes_from(node_list)

            edges = []
            for u,v,e in G.edges(data=True):
                if dfun(e[dynamic_metric], dynamic_threshold) and sfun(e[static_metric], static_threshold):
                #if e['lr'] >= lr_threshold and e['p'] <= p_threshold:
                    edges.append((u,v, e))

            F.add_edges_from(edges)

            graph_degree = F.degree()
            for i, node in enumerate(F.nodes):
                Sub = F.subgraph(neighborhood(F, node, 2))
                n_nodes = len(Sub.nodes)
                n_edges = len(Sub.edges)

                records.append({'node': node,
                                'node_degree': graph_degree[node],
                                'n_nodes': n_nodes,
                                'n_edges': n_edges,
                                dynamic_metric: dynamic_threshold,
                                static_metric: static_threshold,})

        rdf = pd.DataFrame.from_records(records)
        plot = px.histogram(rdf, x='node', y=y, facet_col=dynamic_metric)
        plot.update_layout({'height':800})
        return plot


    ################################################################################
    ### Page Navigation callbacks                                                ###
    ################################################################################
    @app.callback(
        [Output('page-content', 'children'),
        Output('page-1-nav', 'className'),
        Output('page-2-nav', 'className'),
        Output('page-3-nav', 'className'),],
        [Input('url', 'pathname'),]
    )
    def display_page(pathname):
        if pathname == '/page-1':
            return page1_layout, 'active', '', '',
        elif pathname == '/page-2':
            return page2_layout, '', 'active', '',

        elif pathname == '/page-3':
            return page3_layout, '', '', 'active',

        else:
            return landing_page_layout, '', '', '',

    app.run_server(debug=False)