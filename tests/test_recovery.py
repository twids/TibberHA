"""Exercise the actual retry helper without loading HA."""
import asyncio
import importlib.util
from pathlib import Path
import sys
import types


def test_read_recovery_is_bounded_and_does_not_hide_final_error(monkeypatch):
    class TibberError(Exception):
        pass

    monkeypatch.setitem(sys.modules, "tibberlib", types.SimpleNamespace(TibberError=TibberError))
    path = Path(__file__).parents[1] / "custom_components/tibber_ha/recovery.py"
    spec = importlib.util.spec_from_file_location("recovery_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    async def scenario(failures):
        calls = []
        async def read():
            calls.append("read")
            if calls.count("read") <= failures:
                raise TibberError("safe diagnostic")
            return {"id": "zoe"}
        async def authenticate():
            calls.append("authenticate")
        try:
            result = await module.read_with_reauthentication(read, authenticate)
            assert result == {"id": "zoe"}
            assert failures < 2
        except TibberError as err:
            assert failures == 2 and str(err) == "safe diagnostic"
        return calls

    assert asyncio.run(scenario(0)) == ["read"]
    assert asyncio.run(scenario(1)) == ["read", "authenticate", "read"]
    assert asyncio.run(scenario(2)) == ["read", "authenticate", "read"]
