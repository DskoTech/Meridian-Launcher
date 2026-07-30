"""
CyberDeck Browser Field Target

TextInputManager normally targets a QLineEdit
(calls target.setText(...) and
target.returnPressed.emit()). This adapter gives
it the same interface for a focused text field
*inside the loaded web page*, so the shared
onscreen keyboard can type directly into things
like a Google search box.

Uses the native property setter trick so
framework-controlled inputs (React, etc.) notice
the programmatic value change, not just plain
HTML forms.
"""


import json




class _FakeReturnPressed:


    def __init__(
        self,
        submit_fn
    ):

        self._submit_fn = submit_fn



    def emit(self):

        self._submit_fn()




class BrowserFieldTarget:


    def __init__(
        self,
        browser
    ):

        self.browser = browser

        self.returnPressed = _FakeReturnPressed(
            self._submit
        )



    def setText(
        self,
        text
    ):

        if not self.browser:

            return

        escaped = json.dumps(text)

        script = self._build_set_script(
            escaped
        )

        self.browser.page().runJavaScript(
            script
        )



    def _build_set_script(
        self,
        escaped_text
    ):

        return (

            "(function(){"

            "var el = document.activeElement;"

            "if (!el) return;"

            "var proto = (el.tagName === 'TEXTAREA') "

            "? window.HTMLTextAreaElement.prototype "

            ": window.HTMLInputElement.prototype;"

            "var setter = Object.getOwnPropertyDescriptor(proto, 'value');"

            "if (setter && setter.set) {"

            "setter.set.call(el, %s);"

            "} else {"

            "el.value = %s;"

            "}"

            "el.dispatchEvent(new Event('input', {bubbles:true}));"

            "el.dispatchEvent(new Event('change', {bubbles:true}));"

            "})();"

        ) % (

            escaped_text,

            escaped_text

        )



    def _submit(self):

        if not self.browser:

            return

        script = (

            "(function(){"

            "var el = document.activeElement;"

            "if (!el) return;"

            "el.dispatchEvent(new KeyboardEvent("

            "'keydown', {key:'Enter', keyCode:13, which:13, bubbles:true}));"

            "el.dispatchEvent(new KeyboardEvent("

            "'keyup', {key:'Enter', keyCode:13, which:13, bubbles:true}));"

            "if (el.form && el.form.requestSubmit) {"

            "el.form.requestSubmit();"

            "}"

            "})();"

        )

        self.browser.page().runJavaScript(
            script
        )
