import AppKit
import Foundation

final class SelectionView: NSView {
    var startPoint: NSPoint?
    var currentPoint: NSPoint?
    var resultRect: NSRect?

    override var acceptsFirstResponder: Bool { true }
    override var isFlipped: Bool { true }

    override func draw(_ dirtyRect: NSRect) {
        super.draw(dirtyRect)

        NSColor(calibratedWhite: 0, alpha: 0.18).setFill()
        bounds.fill()

        let text = "按住鼠标左键拖拽框选小程序区域，松开后自动保存；按 Esc 取消。"
        let attrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.boldSystemFont(ofSize: 22),
            .foregroundColor: NSColor.white
        ]
        text.draw(at: NSPoint(x: 24, y: 24), withAttributes: attrs)

        guard let start = startPoint, let current = currentPoint else { return }
        let rect = NSRect(
            x: min(start.x, current.x),
            y: min(start.y, current.y),
            width: abs(current.x - start.x),
            height: abs(current.y - start.y)
        )

        NSColor.systemBlue.withAlphaComponent(0.18).setFill()
        rect.fill()

        let path = NSBezierPath(rect: rect)
        path.lineWidth = 3
        NSColor.systemBlue.setStroke()
        path.stroke()
    }

    override func mouseDown(with event: NSEvent) {
        let point = convert(event.locationInWindow, from: nil)
        startPoint = point
        currentPoint = point
        resultRect = nil
        needsDisplay = true
    }

    override func mouseDragged(with event: NSEvent) {
        currentPoint = convert(event.locationInWindow, from: nil)
        needsDisplay = true
    }

    override func mouseUp(with event: NSEvent) {
        guard let start = startPoint else { return }
        let end = convert(event.locationInWindow, from: nil)
        let rect = NSRect(
            x: min(start.x, end.x),
            y: min(start.y, end.y),
            width: abs(end.x - start.x),
            height: abs(end.y - start.y)
        )
        guard rect.width >= 5, rect.height >= 5 else {
            fputs("CANCELLED\n", stdout)
            fflush(stdout)
            NSApp.stop(nil)
            return
        }
        resultRect = rect
        let x = Int(rect.origin.x.rounded())
        let y = Int(rect.origin.y.rounded())
        let width = Int(rect.width.rounded())
        let height = Int(rect.height.rounded())
        fputs("\(x),\(y),\(width),\(height)\n", stdout)
        fflush(stdout)
        NSApp.stop(nil)
    }

    override func keyDown(with event: NSEvent) {
        if event.keyCode == 53 {
            fputs("CANCELLED\n", stdout)
            fflush(stdout)
            NSApp.stop(nil)
            return
        }
        super.keyDown(with: event)
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow?

    func applicationDidFinishLaunching(_ notification: Notification) {
        guard let screen = NSScreen.main else {
            fputs("No active screen\n", stderr)
            NSApp.terminate(nil)
            return
        }

        let frame = screen.frame
        let view = SelectionView(frame: frame)

        let window = NSWindow(
            contentRect: frame,
            styleMask: .borderless,
            backing: .buffered,
            defer: false
        )
        window.level = .screenSaver
        window.backgroundColor = .clear
        window.isOpaque = false
        window.hasShadow = false
        window.ignoresMouseEvents = false
        window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        window.contentView = view
        window.makeKeyAndOrderFront(nil)
        window.center()
        NSApp.activate(ignoringOtherApps: true)
        window.makeFirstResponder(view)
        self.window = window
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.setActivationPolicy(.regular)
app.delegate = delegate
app.run()
