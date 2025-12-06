import dash
from dash import ClientsideFunction, Input, Output, State, dcc, html

PHRASES = [
    {
        "native": "שלום, שמי ח'אלד, אני אכלתי היום עגבניות",
        "arabic_transliteration": "מַרְחַבַּא, אִסְמִי חַ'אלֵד, אַנַא אַכַּלֵת אֵלְיוֹם בַּנְדוֹרַה",
        "hint": "",
    },
    {
        "native": "-ועליכם השלום, שמי דאוּד, הכבוד הוא לי יַא חַ'אלֵד",
        "arabic_transliteration": "וּעַלֵיכֹּם אֵ(ל)סַّלַאם! אִסמִ-י דַאוּד, אֵ(ל)שַّרַף אִלִי יַא חַ'אלֵד!",
        "hint": "",
    },
    # {
    #     "native": "שם משפחתי יוּסף, אני גר בשכונה גדולה",
    #     "hint": "",
    # },
    # {
    #     "native": "אני ישבתי על כיסא גדול",
    #     "hint": "",
    # },
]

app = dash.Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    update_title=None,
)
app.title = "מאמן הגייה ותרגול ערבית לבנטינית"
server = app.server

app.layout = html.Div(
    className="page",
    children=[
        dcc.Store(id="current-phrase-store", data=PHRASES[0]),
        dcc.Store(id="api-response-store"),
        html.Div(id="speech-trigger", style={"display": "none"}),
        html.Div(id="play-trigger", style={"display": "none"}),
        html.Div(id="download-trigger", style={"display": "none"}),
        html.Header(
            className="hero",
            children=[
                html.H1("מאמן הגייה ותרגול ערבית לבנטינית"),
                html.P("תרגל, הקלט, קבל משוב והשתפר בהגייה ובתרגום."),
            ],
        ),
        html.Main(
            className="panel",
            children=[
                html.Div(
                    className="card",
                    children=[
                        html.H2("תרגם והקלט"),
                        html.Div(
                            id="phrase-text",
                            className="phrase",
                            children=f"משפט: {PHRASES[0]['native']}",
                        ),
                        html.Div(
                            id="phrase-hint",
                            className="hint",
                            children=PHRASES[0]["hint"],
                        ),
                        html.Button("משפט הבא", id="next-phrase-btn", className="ghost"),
                        html.P("לחיצה ארוכה להקלטה, ואז שחרור לניתוח."),
                        html.Button("לחצו והחזיקו להקלטה", id="record-button", className="primary"),
                        html.Div(id="output-status", className="status"),
                    ],
                ),
                html.Div(
                    className="card results",
                    children=[
                        html.H2("תוצאות"),
                        html.Div(id="transcription-output", className="result-line"),
                        html.Div(id="compare-output", className="result-line"),
                        html.Div(id="score-output", className="result-line"),
                        html.Div(id="feedback-output", className="result-line"),
                        html.Button("נגן משוב קולי", id="play-feedback-btn", className="ghost"),
                        html.Button("הורד משוב קולי", id="download-feedback-btn", className="ghost"),
                    ],
                ),
            ],
        ),
        html.Footer(
            className="footer",
            children="נבנה ללומדי ערבית לבנטינית. המשיכו להתאמן!",
        ),
    ],
)

app.clientside_callback(
    ClientsideFunction(namespace="audio", function_name="recordAudio"),
    Output("api-response-store", "data"),
    Input("record-button", "n_clicks"),
    State("current-phrase-store", "data"),
)

app.clientside_callback(
    ClientsideFunction(namespace="audio", function_name="speakFeedback"),
    Output("speech-trigger", "children"),
    Input("api-response-store", "data"),
)

app.clientside_callback(
    ClientsideFunction(namespace="audio", function_name="playFeedback"),
    Output("play-trigger", "children"),
    Input("play-feedback-btn", "n_clicks"),
    State("api-response-store", "data"),
)

app.clientside_callback(
    ClientsideFunction(namespace="audio", function_name="downloadFeedback"),
    Output("download-trigger", "children"),
    Input("download-feedback-btn", "n_clicks"),
    State("api-response-store", "data"),
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
    return phrase, f"משפט: {native}", hint


@app.callback(
    [
        Output("transcription-output", "children"),
        Output("compare-output", "children"),
        Output("score-output", "children"),
        Output("feedback-output", "children"),
        Output("output-status", "children"),
    ],
    Input("api-response-store", "data"),
    State("current-phrase-store", "data"),
)
def update_output(data, phrase_data):
    if data is None:
        return "", "", "", "", "לחצו והחזיקו להקלטה כדי להתחיל."

    if "error" in data:
        return "", "", "", "", f"שגיאה: {data['error']}"

    transcription = data.get("transcription") or ""
    feedback = data.get("feedback") or ""
    translation_score = data.get("translation_score") or data.get("score") or 0
    pronunciation_score = data.get("pronunciation_score") or data.get("score") or 0
    target_translit = (phrase_data or {}).get("arabic_transliteration") or ""

    def score_pill(label, icon, score_val):
        pct = max(0, min(int(score_val), 100))
        return html.Div(
            className="score-pill",
            children=[
                html.Div(f"{icon} {label}", className="pill-label"),
                html.Div(
                    className="pill-bar",
                    children=[
                        html.Div(
                            className="pill-fill",
                            style={"width": f"{pct}%"},
                        ),
                        html.Div(f"{pct}%", className="pill-text"),
                    ],
                ),
            ],
        )

    score_block = html.Div(
        className="score-stack",
        children=[
            score_pill("דיוק תרגום", "💬", translation_score),
            score_pill("הגייה", "🎙", pronunciation_score),
        ],
    )

    compare_block = html.Div(
        className="compare-block",
        children=[
            html.Div(
                className="compare-row",
                children=[
                    html.Span("תעתיק יעד", className="compare-label"),
                    html.Span(target_translit or "—", className="compare-text"),
                ],
            ),
            html.Div(
                className="compare-row",
                children=[
                    html.Span("תעתיק משתמש", className="compare-label"),
                    html.Span(transcription or "—", className="compare-text"),
                ],
            ),
        ],
    )

    # We rely on client-side TTS for audio; still show text for clarity.
    return f"תמלול: {transcription}", compare_block, score_block, f"משוב: {feedback}", "מוכן לניגון קולי."



if __name__ == "__main__":
    # Run the combined FastAPI + Dash app to ensure /api/analyze is available.
    import uvicorn

    uvicorn.run("main:server", host="0.0.0.0", port=10000, reload=True)
