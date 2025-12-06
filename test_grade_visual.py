from dash import Dash, html

def score_pill(label, icon, score):
    percent = int(score * 100)
    return html.Div(
        style={
            "display": "flex",
            "alignItems": "center",
            "marginBottom": "4px",
        },
        children=[
            html.Div(
                f"{icon} {label}",
                style={
                    "fontSize": "12px",
                    "width": "90px",
                    "flexShrink": 0,
                    "color": "#444",
                },
            ),
            html.Div(
                style={
                    "position": "relative",
                    "height": "18px",
                    "borderRadius": "999px",
                    "backgroundColor": "#f1f1f1",
                    "flexGrow": 1,
                    "overflow": "hidden",
                },
                children=[
                    html.Div(
                        style={
                            "position": "absolute",
                            "top": 0,
                            "left": 0,
                            "bottom": 0,
                            "width": f"{percent}%",
                            "borderRadius": "999px",
                            "background": "linear-gradient(90deg,#4c6fff,#7fbcff)",
                        }
                    ),
                    html.Div(
                        f"{percent}%",
                        style={
                            "position": "relative",
                            "fontSize": "11px",
                            "textAlign": "center",
                            "lineHeight": "18px",
                            "fontWeight": "500",
                            "color": "#fff" if percent >= 40 else "#333",
                        },
                    ),
                ],
            ),
        ],
    )

def sentence_card(item):
    return html.Div(
        style={
            "borderRadius": "16px",
            "padding": "10px 12px",
            "margin": "8px 0",
            "backgroundColor": "#ffffff",
            "boxShadow": "0 1px 4px rgba(0,0,0,0.08)",
            "display": "flex",
            "flexDirection": "column",
            "gap": "6px",
        },
        children=[
            html.Div(
                item["source"],
                style={
                    "fontSize": "11px",
                    "color": "#888",
                },
            ),
            html.Div(
                item["user_translation"],
                style={
                    "fontSize": "13px",
                    "fontWeight": "600",
                    "color": "#222",
                },
            ),
            html.Div(
                children=[
                    score_pill("Translation", "💬", item["translation_score"]),
                    score_pill("Pronunciation", "🎙", item["pronunciation_score"]),
                ]
            ),
        ],
    )

app = Dash(__name__)

sample_item = {
    "source": "Where is the train station?",
    "user_translation": "Gdzie jest dworzec kolejowy?",
    "translation_score": 0.86,
    "pronunciation_score": 0.72,
}

app.layout = html.Div(
    style={
        "maxWidth": "400px",
        "margin": "0 auto",
        "padding": "8px",
        "backgroundColor": "#f5f5f7",
        "fontFamily": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    },
    children=[
        sentence_card(sample_item)
    ],
)

if __name__ == "__main__":
    app.run(debug=True)
