import dash
from dash import ClientsideFunction, Input, Output, State, dcc, html

PHRASES = [
    {
        "native": "שלום, מה שלומך?",
        "hint": "Say 'Hello, how are you?' in Levantine Arabic.",
    },
    {
        "native": "איפה תחנת האוטובוס הקרובה?",
        "hint": "Ask: Where is the nearest bus station?",
    },
    {
        "native": "תודה רבה, יום טוב.",
        "hint": "Say: Thank you very much, have a good day.",
    },
]

app = dash.Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    update_title=None,
)
app.title = "Levantine Arabic Pronunciation Coach"
server = app.server

app.layout = html.Div(
    className="page",
    children=[
        dcc.Store(id="current-phrase-store", data=PHRASES[0]),
        dcc.Store(id="api-response-store"),
        html.Header(
            className="hero",
            children=[
                html.H1("Levantine Pronunciation Coach"),
                html.P("Record, analyze, and improve your Levantine Arabic pronunciation."),
            ],
        ),
        html.Main(
            className="panel",
            children=[
                html.Div(
                    className="card",
                    children=[
                        html.H2("Translate & Record"),
                        html.Div(
                            id="phrase-text",
                            className="phrase",
                            children=f"Phrase: {PHRASES[0]['native']}",
                        ),
                        html.Div(
                            id="phrase-hint",
                            className="hint",
                            children=PHRASES[0]["hint"],
                        ),
                        html.Button("Next phrase", id="next-phrase-btn", className="ghost"),
                        html.P("Press and hold record, speak the translation, then release to analyze."),
                        html.Button("Hold to Record", id="record-button", className="primary"),
                        html.Div(id="output-status", className="status"),
                    ],
                ),
                html.Div(
                    className="card results",
                    children=[
                        html.H2("Results"),
                        html.Div(id="transcription-output", className="result-line"),
                        html.Div(id="score-output", className="result-line"),
                        html.Div(id="feedback-output", className="result-line"),
                    ],
                ),
            ],
        ),
        html.Footer(
            className="footer",
            children="Built for Levantine learners. Keep practicing!",
        ),
    ],
)

app.clientside_callback(
    ClientsideFunction(namespace="audio", function_name="recordAudio"),
    Output("api-response-store", "data"),
    Input("record-button", "n_clicks"),
    State("current-phrase-store", "data"),
)


@app.callback(
    [
        Output("current-phrase-store", "data"),
        Output("phrase-text", "children"),
        Output("phrase-hint", "children"),
    ],
    Input("next-phrase-btn", "n_clicks"),
)
def set_phrase(n_clicks):
    idx = (n_clicks or 0) % len(PHRASES)
    phrase = PHRASES[idx]
    native = phrase["native"]
    hint = phrase["hint"]
    return phrase, f"Phrase: {native}", hint


@app.callback(
    [
        Output("transcription-output", "children"),
        Output("score-output", "children"),
        Output("feedback-output", "children"),
        Output("output-status", "children"),
    ],
    Input("api-response-store", "data"),
)
def update_output(data):
    if data is None:
        return "", "", "", "Press and hold 'Hold to Record' to start."

    if "error" in data:
        return "", "", "", f"Error: {data['error']}"

    transcription = data.get("transcription")
    score = data.get("score")
    feedback = data.get("feedback")

    return (
        f"Transcription: {transcription}",
        f"Score: {score}/100",
        f"Feedback: {feedback}",
        "Analysis complete.",
    )


if __name__ == "__main__":
    # Run the combined FastAPI + Dash app to ensure /api/analyze is available.
    import uvicorn

    uvicorn.run("main:server", host="0.0.0.0", port=10000, reload=True)
