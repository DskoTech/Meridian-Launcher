// gameinput_native.cpp
//
// pybind11 wrapper around Microsoft's real GameInput SDK (vendored under
// vendor/GameInput/) - replaces the old ctypes vtable-slot-guessing approach.
//
// BUG FIX - Xbox One Bluetooth silent-input:
//   Passing nullptr to GetCurrentReading uses null-aggregation which silently
//   returns all-zero state for Bluetooth-connected Xbox controllers. The fix:
//   register a RegisterDeviceCallback so we always hold the specific device
//   handle, and pass THAT to GetCurrentReading. Hot-plug is handled by the
//   callback updating m_device whenever a pad connects/disconnects.
//
// NOTE - SetInputFocusPolicy is intentionally NOT called:
//   Calling it (any policy) triggers silent all-zero readings for some
//   Bluetooth devices on certain driver versions. Omitting it gives us
//   background input by default - exactly what Meridian needs.

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <Windows.h>
#include <GameInput.h>

#include <mutex>
#include <string>

namespace py = pybind11;
using namespace GameInput::v3;

// Sentinel for "no callback registered yet". GameInputCallbackToken is a
// uint64_t typedef; 0 is never a valid token value from RegisterDeviceCallback.
static constexpr GameInputCallbackToken kNoToken = 0;

// Translate GameInput button bitmask to XInput-compatible bitmask so
// gameinput_api.py's XI_BUTTONS table and all downstream logic needs
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

        // Register a device-arrival/removal callback. This is the Bluetooth
        // fix: by tracking the specific device handle we bypass the
        // null-aggregation path that silently zeros out BT controller state.
        hr = m_gameInput->RegisterDeviceCallback(
            nullptr,                    // no filter: all devices
            GameInputKindGamepad,       // gamepad-kind only
            GameInputDeviceNoStatus,    // all status changes
            GameInputBlockingEnumeration,
            this,
            &GameInputPad::OnDeviceCallback,
            &m_callbackToken
        );
        // Non-fatal: if registration fails we fall back to null-device polling
        // (same as before the BT fix). Everything else still works.
        if (FAILED(hr))
            m_callbackToken = kNoToken;
    }

    ~GameInputPad()
    {
        if (m_gameInput)
        {
            // UnregisterCallback(token) — one argument, returns bool.
            if (m_callbackToken != kNoToken)
                m_gameInput->UnregisterCallback(m_callbackToken);

            {
                std::lock_guard<std::mutex> lk(m_deviceMutex);
                if (m_device) { m_device->Release(); m_device = nullptr; }
            }
            m_gameInput->Release();
            m_gameInput = nullptr;
        }
    }

    // Returns (buttons, lt, rt, lx, ly, rx, ry, raw_buttons, timestamp_us)
    // or None when no gamepad reading is available.
    //
    // raw_buttons = untranslated GameInputGamepadButtons bitmask (diagnostic).
    // timestamp_us = GetTimestamp() in microseconds (diagnostic).
    // If raw_buttons is always 0 despite real presses the BT null-agg bug is
    // still active somehow; if timestamp_us never changes GetCurrentReading is
    // returning a cached stale reading.
    py::object Poll()
    {
        // Prefer the specific device handle (BT fix).
        // Fall back to nullptr (null-aggregation) if the callback hasn't
        // fired yet or registration failed.
        IGameInputDevice* device = nullptr;
        {
            std::lock_guard<std::mutex> lk(m_deviceMutex);
            device = m_device;
            if (device) device->AddRef();
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
    // GameInput calls this on its own background thread. Must be fast.
    static void CALLBACK OnDeviceCallback(
        _In_ GameInputCallbackToken /*token*/,
        _In_ void*                  context,
        _In_ IGameInputDevice*      device,
        _In_ uint64_t               /*timestamp*/,
        _In_ GameInputDeviceStatus  currentStatus,
        _In_ GameInputDeviceStatus  /*previousStatus*/)
    {
        auto* self = static_cast<GameInputPad*>(context);
        std::lock_guard<std::mutex> lk(self->m_deviceMutex);

        const bool connected = (currentStatus & GameInputDeviceConnected) != 0;

        if (connected)
        {
            // First connected gamepad wins (same single-controller convention
            // as XInputGetState slot-0 polling).
            if (!self->m_device)
            {
                self->m_device = device;
                self->m_device->AddRef();
            }
        }
        else
        {
            if (self->m_device == device)
            {
                self->m_device->Release();
                self->m_device = nullptr;
            }
        }
    }

    IGameInput*            m_gameInput    = nullptr;
    IGameInputDevice*      m_device       = nullptr; // guarded by m_deviceMutex
    std::mutex             m_deviceMutex;
    GameInputCallbackToken m_callbackToken = kNoToken;
};

PYBIND11_MODULE(gameinput_native, m)
{
    m.doc() =
        "Real Microsoft GameInput SDK bindings. "
        "Uses device-callback enumeration to fix Xbox One Bluetooth "
        "silent-input bug (see file header).";

    py::class_<GameInputPad>(m, "GameInputPad")
        .def(py::init<>())
        .def("poll", &GameInputPad::Poll,
             "Returns (buttons, lt, rt, lx, ly, rx, ry, raw_buttons, "
             "timestamp_us) or None.");
}
