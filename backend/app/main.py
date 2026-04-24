from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from backend.app.api.router import api_router
from backend.app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    openapi_url=f"{settings.api_prefix}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def backend_gui() -> str:
    return """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>OpsMesh API</title>
    <style>
      :root {
        color-scheme: dark;
        --bg: #0b1020;
        --card: #141b2d;
        --text: #e8eefc;
        --muted: #9cb0d1;
        --accent: #4ea1ff;
        --border: rgba(255, 255, 255, 0.12);
      }
      body {
        margin: 0;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
        background: radial-gradient(120% 80% at 20% 0%, #1f2b45 0%, var(--bg) 45%);
        color: var(--text);
      }
      .wrap {
        max-width: 920px;
        margin: 0 auto;
        padding: 40px 20px;
      }
      .card {
        border: 1px solid var(--border);
        border-radius: 14px;
        background: color-mix(in srgb, var(--card) 88%, transparent);
        backdrop-filter: blur(10px);
        padding: 22px;
      }
      h1 { margin: 0 0 6px; font-size: 28px; }
      p { margin: 0; color: var(--muted); }
      .grid {
        margin-top: 20px;
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 12px;
      }
      a {
        display: block;
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 12px 14px;
        text-decoration: none;
        color: var(--text);
        background: rgba(255, 255, 255, 0.03);
      }
      a:hover { border-color: var(--accent); }
      .small { margin-top: 16px; font-size: 13px; color: var(--muted); }
      code { color: var(--accent); }
    </style>
  </head>
  <body>
    <main class="wrap">
      <section class="card">
        <h1>OpsMesh API</h1>
        <p>Backend is running. Use the links below to inspect health, docs, and auth routes.</p>
        <div class="grid">
          <a href="/api/v1/health">Health Check<br /><small>/api/v1/health</small></a>
          <a href="/docs">Swagger UI<br /><small>/docs</small></a>
          <a href="/redoc">ReDoc<br /><small>/redoc</small></a>
          <a href="/api/v1/openapi.json">OpenAPI JSON<br /><small>/api/v1/openapi.json</small></a>
        </div>
        <p class="small">Tip: frontend should use <code>NEXT_PUBLIC_API_URL=http://localhost:8000</code>.</p>
      </section>
    </main>
  </body>
</html>
    """


app.include_router(api_router, prefix=settings.api_prefix)
