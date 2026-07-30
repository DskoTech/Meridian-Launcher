// gameinput_native.cpp
//
// pybind11 wrapper around Microsoft's real GameInput SDK.
//
// BUG FIX (Bluetooth Xbox One controller silent-input bug):
//   The previous implementation called GetCurrentReading(GameInputKindGamepad,
//   nullptr, &reading) — passing nullptr as the device, which tells GameInput
//   to aggregate all connected gamepads into one reading. This works over USB
//   but silently fails over Bluetooth: GameInput hands back a reading object
//   whose GetGamepadState() returns ok=true but all fields (buttons, sticks,
//   triggers) are permanently zero. This is a confirmed GameInput bug against
//   Bluetooth-connected Xbox controllers (github.com/microsoft/GDK/issues/70).
//
//   The fix: register a RegisterDeviceCallback to track the first connected
//   gamepad device handle explicitly, then pass THAT handle to GetCurrentReading.
//   This bypasses the null-aggregation path that silently drops BT input.
//   Hot-plug (controller connecting after the app starts) is handled by the
//   callback updating m_device whenever a gamepad arrives or leaves.
//
//   We also do NOT call SetInputFocusPolicy — calling it (even with what
//   looks like a sensible policy) is known to trigger the silent-input
//   condition on some driver versions. Omitting it gives us background input
//   by default, which is exactly what the Meridian Launcher needs (the whole
//   point is controller-driven navigation while other apps are running).

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <Windows.h>
#include <GameInput.h>

#include <mutex>
#include <string>

namespace py = pybind11;
using namespace GameInput::v3;

// GameInput's own bitmask (GameInputGamepadButtons) uses different bit
// positions than XInput's XINPUT_GAMEPAD_* constants. Translating here
// means gameinput_api.py's XI_BUTTONS and everything downstream needs
// zero changes.
static uint32_t TranslateButtons(GameInputGamepadButtons b)
{
    uint32_t out = 0;
    if (b & GameInputGamepadDPadUp)          out |= 0x0001;
    if (b & GameInputGamepadDPadDown)        out |= 0x0002;
    if (b & GameInputGamepadDPadLeft)        out |= 0x0004;
    if (b & GameInputGamepadDPadRight)       out |= 0x0008;
    if (b & GameInputGamepadMenu)            out |= 0x0010; // Start
    if (b & GameInputGamepadView)            out |= 0x0020; // Back
    if (b & GameInputGamepadLeftThumbstick)  out |= 0x0040;
    if (b & GameInputGamepadRightThumbstick) out |= 0x0080;
    if (b & GameInputGamepadLeftShoulder)    out |= 0x0100;
    if (b & GameInputGamepadRightShoulder)   out |= 0x0200;
    if (b & GameInputGamepadA)               out |= 0x1000;
    if (b & GameInputGamepadB)               out |= 0x2000;
    if (b & GameInputGamepadX)               out |= 0x4000;
    if (b & GameInputGamepadY)               out |= 0x8000;
    return out;
}

static std::string HrHex(HRESULT hr)
{
    char buf[16];
    snprintf(buf, sizeof(buf), "%08lX", static_cast<unsigned long>(hr));
    return std::string(buf);
}

class GameInputPad
{
public:
    GameInputPad()
    {
        HRESULT hr = GameInputCreate(&m_gameInput);
        if (FAILED(hr) || !m_gameInput)
            throw std::runtime_error("GameInputCreate failed (hr=0x" + HrHex(hr) + ")");

        // Register a device-arrival/removal callback so we always have the
        // specific device handle for the first connected gamepad. This is the
        // fix for the Bluetooth silent-input bug: passing a real device handle
        // to GetCurrentReading instead of nullptr bypasses the null-aggregation
        // path that silently drops Bluetooth input.
        //
        // GameInputDeviceNoStatus means we get called for every status change
        // (connected, disconnected, input-enabled, etc). We only track
        // connected gamepads, so every non-gamepad device and every
        // disconnection just updates m_device to nullptr.
        hr = m_gameInput->RegisterDeviceCallback(
            nullptr,                    // no filter: all devices
            GameInputKindGamepad,       // only gamepad-kind devices
            GameInputDeviceNoStatus,    // all status changes
            GameInputBlockingEnumeration,
            this,
            &GameInputPad::OnDeviceCallback,
            &m_callbackToken
        );
        // Registration failure is non-fatal: Poll() will fall back to the
        // null-device path (same as before), and the BT bug may still
        // occur — but that's no worse than before this fix, and everything
        // else still works. Log it via the existing HRESULT path.
        if (FAILED(hr))
            m_callbackToken = GAMEINPUT_INVALID_CALLBACK_TOKEN_VALUE;
    }

    ~GameInputPad()
    {
        // Unregister before releasing so the callback doesn't fire after
        // m_gameInput is gone.
        if (m_gameInput)
        {
            if (m_callbackToken != GAMEINPUT_INVALID_CALLBACK_TOKEN_VALUE)
                m_gameInput->UnregisterCallback(m_callbackToken, 5000 /*ms wait*/);

            {
                std::lock_guard<std::mutex> lk(m_deviceMutex);
                if (m_device) { m_device->Release(); m_device = nullptr; }
            }
            m_gameInput->Release();
            m_gameInput = nullptr;
        }
    }

    // Returns a 9-tuple (buttons, lt, rt, lx, ly, rx, ry, raw_buttons,
    // timestamp_us) matching gameinput_api.py's GamepadSnapshot field
    // order plus two diagnostic extras, or None if no gamepad reading
    // is currently available.
    //
    // raw_buttons is the untranslated GameInputGamepadButtons bitmask
    // (before TranslateButtons). timestamp_us is GetTimestamp() in
    // microseconds. Both were added to diagnose the "reads successfully
    // but all fields are always zero" Bluetooth bug:
    //   - raw_buttons always 0 despite presses -> GameInput itself isn't
    //     seeing this device's input (Bluetooth null-aggregation bug or
    //     a driver issue). This is the bug the device-callback fix above
    //     addresses.
    //   - timestamp_us never changes -> GetCurrentReading is returning
    //     the same cached reading every call (a state-refresh bug).
    //   - raw_buttons shows presses but translated buttons don't ->
    //     TranslateButtons has a bug worth re-auditing bit-by-bit.
    py::object Poll()
    {
        // Prefer the specific device handle from the callback (BT fix).
        // Fall back to nullptr (null-aggregation) if no device has been
        // seen yet or registration failed.
        IGameInputDevice* device = nullptr;
        {
            std::lock_guard<std::mutex> lk(m_deviceMutex);
            device = m_device;
            if (device) device->AddRef(); // keep alive for the duration of Poll()
        }

        IGameInputReading* reading = nullptr;
        HRESULT hr = m_gameInput->GetCurrentReading(GameInputKindGamepad, device, &reading);

        if (device) device->Release();

        if (FAILED(hr) || !reading)
            return py::none();

        GameInputGamepadState state{};
        bool ok = reading->GetGamepadState(&state);
        uint64_t timestampUs = reading->GetTimestamp();
        reading->Release();

        if (!ok)
            return py::none();

        uint32_t buttons = TranslateButtons(state.buttons);
        return py::make_tuple(
            buttons,
            state.leftTrigger,
            state.rightTrigger,
            state.leftThumbstickX,
            state.leftThumbstickY,
            state.rightThumbstickX,
            state.rightThumbstickY,
            static_cast<uint32_t>(state.buttons), // raw_buttons (diagnostic)
            timestampUs                            // timestamp_us (diagnostic)
        );
    }

private:
    // Called by GameInput on the background thread it manages for callbacks.
    // Must be fast and not block; m_deviceMutex guards m_device.
    static void CALLBACK OnDeviceCallback(
        _In_ GameInputCallbackToken /*token*/,
        _In_ void* context,
        _In_ IGameInputDevice* device,
        _In_ uint64_t /*timestamp*/,
        _In_ GameInputDeviceStatus currentStatus,
        _In_ GameInputDeviceStatus /*previousStatus*/)
    {
        auto* self = static_cast<GameInputPad*>(context);
        std::lock_guard<std::mutex> lk(self->m_deviceMutex);

        const bool connected =
            (currentStatus & GameInputDeviceConnected) != 0;

        if (connected)
        {
            // First connected gamepad wins. If we already have one and a
            // second connects, keep the first (same single-controller
            // convention as XInputGetState slot-0 polling).
            if (!self->m_device)
            {
                self->m_device = device;
                self->m_device->AddRef();
            }
        }
        else
        {
            // This device disconnected — clear our handle if it's the one
            // we were using. The next connected callback will set a new one.
            if (self->m_device == device)
            {
                self->m_device->Release();
                self->m_device = nullptr;
            }
        }
    }

    IGameInput*           m_gameInput    = nullptr;
    IGameInputDevice*     m_device       = nullptr;  // guarded by m_deviceMutex
    std::mutex            m_deviceMutex;
    GameInputCallbackToken m_callbackToken = GAMEINPUT_INVALID_CALLBACK_TOKEN_VALUE;
};

PYBIND11_MODULE(gameinput_native, m)
{
    m.doc() = "Real Microsoft GameInput SDK bindings for gamepad state "
              "(uses device-callback enumeration to fix Xbox One Bluetooth "
              "silent-input bug — see the file header for details).";

    py::class_<GameInputPad>(m, "GameInputPad")
        .def(py::init<>())
        .def("poll", &GameInputPad::Poll,
             "Returns (buttons, lt, rt, lx, ly, rx, ry, raw_buttons, "
             "timestamp_us) or None.");
}

//
// WHY THIS EXISTS
// -----------------
// The previous implementation didn't have real GameInput headers to
// build against, so it called into gameinput.dll via raw ctypes vtable
// slot indices it had to guess (starting from slot 23, falling back to
// 22/24/21/25, with a whole "probation" mechanism to avoid trusting a
// wrong slot's garbage memory - see gameinput_api.py's docstring history
// for the full story). With the real SDK now available (Microsoft's
// public NuGet package, vendored here), none of that guessing is
// necessary: the real IID_IGameInput is 20EFC1C7-5D9A-43BA-B26F-
// B807FA48609C (NOT the value the old code had, which explains a lot),
// and the real header confirms IGameInputReading::GetGamepadState sits
// at vtable slot 18 (3 IUnknown methods + 15 IGameInputReading methods
// before it: GetInputKind, GetTimestamp, GetDevice, GetControllerAxis-
// Count/State, GetControllerButtonCount/State, GetControllerSwitchCount/
// State, GetKeyCount/State, GetMouseState, GetSensorsState,
// GetArcadeStickState, GetFlightStickState) - not the 22 or 23 the old
// code tried. The C++ compiler resolves all of this correctly from the
// real interface declaration; nothing here is guessed.
//
// WHAT THIS DOES
// ----------------
// One class, GameInputPad:
//   - Constructor calls the real GameInputCreate() once.
//   - poll() calls IGameInput::GetCurrentReading(GameInputKindGamepad,
//     nullptr, &reading) - passing a null device aggregates every
//     connected gamepad into one reading, matching how XInputGetState
//     behaves for "the" controller rather than needing per-device
//     enumeration - then IGameInputReading::GetGamepadState() to get the
//     actual buttons/sticks/triggers. Returns None (via std::optional)
//     when nothing is connected/no reading is available, same contract
//     as gameinput_api.py's other backends' poll() methods.
//   - The returned buttons bitmask is translated to the exact same bit
//     values gameinput_api.py's XI_BUTTONS already uses (real
//     XINPUT_GAMEPAD_* values) - GameInput's own GameInputGamepadButtons
//     enum uses different bit positions - so nothing downstream of
//     poll() in gameinput_api.py needs to change at all.
//
// BUILDING
// ---------
// Needs the MSVC toolchain (Visual Studio Build Tools) and pybind11.
// From this folder:
//     pip install pybind11 --break-system-packages
//     python setup.py build_ext --inplace
// Produces gameinput_native.<tag>.pyd - copy it next to gameinput_api.py
// in every app folder that uses it (same distribution convention as
// SDL3.dll). See this folder's README.md for the full walkthrough and
// the runtime DLL requirement (gameinput.dll itself, from
// vendor/GameInput/redist - most gaming-oriented Windows installs
// already have it, but it's not guaranteed).
//
// gameinput_api.py imports this module opportunistically: if it's not
// present (not yet built, or on a non-Windows dev machine), the old
// ctypes-based GameInputGamepad implementation is still there as a
// fallback so nothing breaks - but this native module is now the
// correct, authoritative implementation whenever it's available.

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <Windows.h>
#include <GameInput.h>

namespace py = pybind11;
using namespace GameInput::v3;

// GameInput's own bitmask (GameInputGamepadButtons) uses different bit
// positions than XInput's XINPUT_GAMEPAD_* constants. Translating here
// means gameinput_api.py's XI_BUTTONS / GamepadSnapshot / every button-
// name-based consumer elsewhere in the app needs zero changes - this
// native module speaks the same bitmask "language" XInputGamepad and
// DirectInputGamepad already do.
static uint32_t TranslateButtons(GameInputGamepadButtons b)
{
    uint32_t out = 0;
    if (b & GameInputGamepadDPadUp)        out |= 0x0001;
    if (b & GameInputGamepadDPadDown)      out |= 0x0002;
    if (b & GameInputGamepadDPadLeft)      out |= 0x0004;
    if (b & GameInputGamepadDPadRight)     out |= 0x0008;
    if (b & GameInputGamepadMenu)          out |= 0x0010; // Start
    if (b & GameInputGamepadView)          out |= 0x0020; // Back
    if (b & GameInputGamepadLeftThumbstick)  out |= 0x0040;
    if (b & GameInputGamepadRightThumbstick) out |= 0x0080;
    if (b & GameInputGamepadLeftShoulder)  out |= 0x0100;
    if (b & GameInputGamepadRightShoulder) out |= 0x0200;
    if (b & GameInputGamepadA)             out |= 0x1000;
    if (b & GameInputGamepadB)             out |= 0x2000;
    if (b & GameInputGamepadX)             out |= 0x4000;
    if (b & GameInputGamepadY)             out |= 0x8000;
    // GameInput has no separate "Guide/Xbox button" bit in
    // GameInputGamepadButtons at all (unlike XInputGetStateEx's
    // undocumented bit 0x0400) - there simply isn't one to translate.
    // gameinput_api.py's GUIDE bit just never sets when this backend is
    // active, same as when the plain public XInputGetState is used
    // instead of the Ex variant; callers already treat that as normal
    // ("when it isn't available this bit simply never sets").
    return out;
}

class GameInputPad
{
public:
    GameInputPad()
    {
        HRESULT hr = GameInputCreate(&m_gameInput);
        if (FAILED(hr) || !m_gameInput)
        {
            throw std::runtime_error("GameInputCreate failed (hr=0x" + HrHex(hr) + ")");
        }
    }

    ~GameInputPad()
    {
        if (m_gameInput)
        {
            m_gameInput->Release();
            m_gameInput = nullptr;
        }
    }

    // Returns a 9-tuple (buttons, lt, rt, lx, ly, rx, ry, raw_buttons,
    // timestamp_us) matching gameinput_api.py's GamepadSnapshot field
    // order plus two diagnostic-only extras, or None if no gamepad
    // reading is currently available (nothing connected, or the read
    // genuinely failed this instant - same "just means try again next
    // poll" contract every other backend already has).
    //
    // raw_buttons is the UNTRANSLATED GameInputGamepadButtons bitmask
    // (before TranslateButtons runs) and timestamp_us is
    // IGameInputReading::GetTimestamp() in microseconds - both added
    // specifically to debug a real "reads successfully (ok=true) but
    // buttons_seen/stick_moved never leave their zeroed defaults, even
    // with genuine button presses during the test window" report:
    //   - if raw_buttons is ALSO always 0 despite real presses, that
    //     proves GameInput itself isn't seeing this controller's input
    //     (wrong/phantom device via the null-device aggregation this
    //     class uses, or a driver-level issue) - TranslateButtons isn't
    //     the problem.
    //   - if timestamp_us never changes across many polls, that proves
    //     GetCurrentReading is handing back the SAME cached reading
    //     over and over rather than a fresh one each call - a state-
    //     refresh bug distinct from either of the above.
    //   - if raw_buttons shows real presses but the translated buttons
    //     field the rest of the app sees doesn't, TranslateButtons
    //     itself has a bug worth re-auditing bit-by-bit.
    py::object Poll()
    {
        IGameInputReading* reading = nullptr;
        HRESULT hr = m_gameInput->GetCurrentReading(GameInputKindGamepad, nullptr, &reading);
        if (FAILED(hr) || !reading)
        {
            return py::none();
        }

        GameInputGamepadState state{};
        bool ok = reading->GetGamepadState(&state);
        uint64_t timestampUs = reading->GetTimestamp();
        reading->Release();

        if (!ok)
        {
            return py::none();
        }

        uint32_t buttons = TranslateButtons(state.buttons);
        return py::make_tuple(
            buttons,
            state.leftTrigger,
            state.rightTrigger,
            state.leftThumbstickX,
            state.leftThumbstickY,
            state.rightThumbstickX,
            state.rightThumbstickY,
            static_cast<uint32_t>(state.buttons),
            timestampUs
        );
    }

private:
    static std::string HrHex(HRESULT hr)
    {
        char buf[16];
        snprintf(buf, sizeof(buf), "%08lX", static_cast<unsigned long>(hr));
        return std::string(buf);
    }

    IGameInput* m_gameInput = nullptr;
};

PYBIND11_MODULE(gameinput_native, m)
{
    m.doc() = "Real Microsoft GameInput SDK bindings for gamepad state "
              "(replaces the old ctypes vtable-guessing approach).";

    py::class_<GameInputPad>(m, "GameInputPad")
        .def(py::init<>())
        .def("poll", &GameInputPad::Poll,
             "Returns (buttons, lt, rt, lx, ly, rx, ry) or None.");
}
