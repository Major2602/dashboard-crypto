# APP LAYOUT


app = dash.Dash(__name__)
update_time = datetime.now(timezone.utc).strftime("%d %B %Y %H:%M:%S UTC")

app.layout = dmc.MantineProvider(
    id="mantine-provider",
    defaultColorScheme="dark",
    children=dmc.Container([

        # Header Section
        dmc.Paper([
            dmc.Group([
                dmc.Group(
                    dmc.Title("Crypto Sentiment & Market Dashboard",
                              id='main-title',
                              order=2,
                              style={'fontWeight': 800, 'letterSpacing': '-0.5px'})
                ),
                dmc.Group([
                    dmc.Group([
                        DashIconify(icon="radix-icons:sun", width=18),
                        dmc.Switch(id="theme-toggle", size="md", checked=True),
                        DashIconify(icon="radix-icons:moon", width=18),
                    ], gap="xs"),
                    dmc.Badge(f"Last Updated: {update_time}", variant="dot", size="lg", color="green"),
                ], gap="sm")
            ], justify="space-between", p="md")
        ], withBorder=True, mb="xl", radius="md", shadow="xs"),

        dmc.Grid([

            # Column 1
            dmc.GridCol([
                dmc.Stack([dmc.Paper(
                    dmc.Stack([
                        dmc.Stack([
                            dmc.Text("Controls", fw=700, size="lg", c="blue", mb=0),
                            dmc.Divider(mb="xs"),
                            ], gap=0),
                        dmc.Stack([
                            dmc.Text("Tickers", fw=600, size="sm"),
                            dmc.MultiSelect(id="ticker-select", data=[{'label': t, 'value': t} for t in Config.TARGET_TICKERS], value=Config.TARGET_TICKERS),
                            ], gap=2),
                        dmc.Stack([
                            dmc.Text("Period", fw=600, size="sm"),
                            dmc.DatePickerInput(id="date-range", type="range", minDate=DF_REPORT['date'].min().date(), maxDate=DF_REPORT['date'].max().date(), value=[DF_REPORT['date'].min().date(), DF_REPORT['date'].max().date()]),
                            dmc.Group([
                                dmc.Button("1M", id="btn-1m", variant="outline", size="xs"),
                                dmc.Button("3M", id="btn-3m", variant="outline", size="xs"),
                                dmc.Button("6M", id="btn-6m", variant="outline", size="xs")
                                ], grow=True, gap="xs", mt="xs"),
                            dmc.Group([
                                dmc.Button("9M", id="btn-9m", variant="outline", size="xs"),
                                dmc.Button("12M", id="btn-12m", variant="outline", size="xs"),
                                dmc.Button("All", id="btn-all", variant="outline", size="xs")
                                ], grow=True, gap="xs", mt="xs")
                            ], gap=2),
                        ], gap="sm"), withBorder=True, p="md", radius="md", shadow="sm", style={'flex': 1}),
                           dmc.Paper([
                               dmc.Stack([
                                   dmc.Text("Linear Regression", fw=700, size="md", ta="center"),
                                   dmc.Divider(),
                                   html.Div(id='regression-container')
                                   ], gap="xs")
                           ], withBorder=True, p="md", radius="md", shadow="sm", style={'flex': 1})
                           ], gap="md", style={'height': '100%'})
                ], span=2, style={'display': 'flex', 'flexDirection': 'column'}),

            # Column 2
            dmc.GridCol([
                dmc.Stack([
                    dmc.Paper([html.Div(id="perf-panels-top")],
                              withBorder=True, p=15, radius="md", shadow="sm"),
                    dmc.Paper([
                        dmc.Stack([
                            dmc.Text("Price Performance & Reference Dynamics", fw=700, size="lg", mt="md", ta="center"),
                            dmc.Paper([
                                dcc.Graph(id='main-price-graph', style={'height': '600px'})
                                ], withBorder=True, radius="md", shadow="sm", mb="md", ml="md", mr="md")])
                        ], withBorder=True, radius="md", shadow="sm", style={'flex': 1}),
                    dmc.Paper([
                        dmc.Text("Context (LLM Summarized)", fw=700, size="lg", mb="md", style={'textAlign': 'center'}),
                        dash_table.DataTable(
                            id='topics-table',
                            page_size=10,
                            columns=[
                                {"name": "Date", "id": "date"},
                                 {"name": "Topics", "id": "clean_topics", "presentation": "markdown"}
                                ],
                            style_table={'height': '500px', 'overflowY': 'auto'})
                        ], withBorder=True, p="md", radius="md", shadow="sm", style={'display': 'flex', 'flexDirection': 'column', 'flex': 1}),
                    ], gap="md", style={'height': '100%'})
            ], span=7, style={'display': 'flex', 'flexDirection': 'column'}),

            # Column 3
            dmc.GridCol([
                dmc.Stack([
                    dmc.Paper([
                        dmc.Stack([
                            dmc.Text("Multiparametric Comparison", fw=700, size="lg", mt="md", ta="center"),
                            dmc.Paper([
                                dcc.Graph(id='radar-graph', style={'height': '400px'}),
                            ], withBorder=True, radius="md", shadow="sm", mb='md', ml="md", mr="md")])
                        ], withBorder=True, radius="md", shadow="sm", style={'flex': 1}),
                    dmc.Paper([
                        dmc.Stack([
                            dmc.Text("Price Correlation", fw=700, size="lg", mt="md", ta="center"),
                            dmc.Paper([dcc.Graph(id='corr-price', style={'height': '350px'}),
                        ], withBorder=True, radius="md", shadow="sm", mb="md", ml="md", mr="md")])
                    ], withBorder=True, radius="md", shadow="sm", style={'flex': 1}),
                    dmc.Paper([
                        dmc.Stack([
                            dmc.Text("Reference Correlation", fw=700, size="lg", mt="md", ta="center"),
                            dmc.Paper([
                                dcc.Graph(id='corr-ref', style={'height': '350px'}),
                        ], withBorder=True, radius="md", shadow="sm", mb="md", ml="md", mr="md")])
                    ], withBorder=True, radius="md", shadow="sm", style={'flex': 1})
                    ], gap="md", style={'height': '100%'})
                ], span=3, style={'display': 'flex', 'flexDirection': 'column'})


            ], gutter="md", mb="md", align="stretch")
        ], fluid=True, p="md")
    )
