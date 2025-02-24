from __future__ import annotations as _annotations

from dataclasses import dataclass
from datetime import timezone

import pytest
from inline_snapshot import snapshot

from pydantic_graph import (
    BaseNode,
    End,
    EndSnapshot,
    FullStatePersistence,
    Graph,
    GraphRunContext,
    NodeSnapshot,
)

from ..conftest import IsFloat, IsNow

pytestmark = pytest.mark.anyio


async def test_run_graph():
    @dataclass
    class MyState:
        x: int
        y: str

    @dataclass
    class Foo(BaseNode[MyState]):
        async def run(self, ctx: GraphRunContext[MyState]) -> Bar:
            ctx.state.x += 1
            return Bar()

    @dataclass
    class Bar(BaseNode[MyState, None, str]):
        async def run(self, ctx: GraphRunContext[MyState]) -> End[str]:
            ctx.state.y += 'y'
            return End(f'x={ctx.state.x} y={ctx.state.y}')

    graph = Graph(nodes=(Foo, Bar))
    assert graph._inferred_types == (MyState, str)  # pyright: ignore[reportPrivateUsage]
    state = MyState(1, '')
    sp = FullStatePersistence()
    result = await graph.run(Foo(), state=state, persistence=sp)
    assert result == snapshot('x=2 y=y')
    assert sp.history == snapshot(
        [
            NodeSnapshot(
                state=MyState(x=1, y=''),
                node=Foo(),
                start_ts=IsNow(tz=timezone.utc),
                duration=IsFloat(),
            ),
            NodeSnapshot(
                state=MyState(x=2, y=''),
                node=Bar(),
                start_ts=IsNow(tz=timezone.utc),
                duration=IsFloat(),
            ),
            EndSnapshot(state=MyState(x=2, y='y'), result=End('x=2 y=y'), ts=IsNow(tz=timezone.utc)),
        ]
    )
    assert state == MyState(x=2, y='y')
