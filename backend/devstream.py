"""Expose the FastAPI application under this container's Devstream URL prefix."""
from __future__ import annotations
import os
from .app import app

PREFIX = os.environ.get('DEVSTREAM_BASE_URL_8501', '').rstrip('/')

async def application(scope, receive, send):
    if scope['type'] not in ('http', 'websocket') or not PREFIX:
        await app(scope, receive, send)
        return
    path = scope.get('path', '')
    if path != PREFIX and not path.startswith(PREFIX + '/'):
        if scope['type'] == 'http':
            await send({'type': 'http.response.start', 'status': 404, 'headers': []})
            await send({'type': 'http.response.body', 'body': b'Not Found'})
        return
    local_scope = dict(scope)
    local_scope['root_path'] = PREFIX
    local_scope['path'] = path[len(PREFIX):] or '/'
    await app(local_scope, receive, send)
