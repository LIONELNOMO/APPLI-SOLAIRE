# -*- mode: python ; coding: utf-8 -*-
"""Configuration PyInstaller du sidecar (§13.2 d'ARCHITECTURE.md).

Uvicorn charge ses boucles et protocoles dynamiquement : sans `hiddenimports`,
l'exécutable démarre puis échoue au premier appel.
"""

from pathlib import Path

RACINE = Path(SPECPATH)

a = Analysis(
    ["run_server.py"],
    pathex=[str(RACINE)],
    binaries=[],
    datas=[
        ("app/db/seed", "app/db/seed"),
        ("alembic.ini", "."),
        ("alembic", "alembic"),
    ],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "app.main",
        "app.engine.pipeline",
        # Dialectes SQLAlchemy résolus par nom au démarrage.
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.sql.default_comparator",
    ],
    hookspath=[],
    runtime_hooks=[],
    # pandas, numpy et matplotlib ne sont pas utilisés : les exclure évite
    # qu'une dépendance transitive les embarque et alourdisse l'exécutable.
    # Pillow (PIL) ne peut pas être exclu : ReportLab 4 en dépend.
    excludes=["tkinter", "matplotlib", "numpy", "pandas", "pytest", "IPython"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="dimsolaire-api",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
