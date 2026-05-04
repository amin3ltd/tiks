import pytest
from compressor.exceptions import FilterError
from django.test import override_settings

from pretix.helpers.compressor import VueCompiler


VUE_COMPONENT = "src/pretix/static/pretixcontrol/js/ui/checkinrules/checkin-rules-editor.vue"


@override_settings(DEBUG=True)
def test_vue_compiler_debug_fallback_without_rollup():
    compiler = VueCompiler('', {}, filename=VUE_COMPONENT)

    output = compiler.input()

    assert "window.CheckinRulesEditor = {default: component};" in output
    assert "component.template" in output


@override_settings(DEBUG=False)
def test_vue_compiler_requires_rollup_outside_debug():
    with pytest.raises(FilterError):
        VueCompiler('', {}, filename=VUE_COMPONENT)
