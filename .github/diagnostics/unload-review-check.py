import pathlib
import subprocess
import sys
import tempfile

source = pathlib.Path(sys.argv[1]).read_text()
start = source.index('    @discardableResult\n    private func unload(')
end = source.index('\n    private func save()', start)
method = source[start:end].replace('private func unload', 'func unload')
stubs = r'''
import Foundation
var events: [String] = []
enum Refused: Error { case unload }
final class Context {}
final class Controller {
    var fail = false
    func unload(_ context: Context) throws {
        events.append("unload")
        if fail { throw Refused.unload }
    }
}
final class Port {
    var disconnectHandler: ((Int?) -> Void)? = { _ in events.append("host/socket cleanup") }
    var isDisconnected = false
    func disconnect() { events.append("disconnect"); isDisconnected = true }
}
final class Ports { var allObjects = [Port()] }
final class ExtensionWorkerRecovery {
    static let shared = ExtensionWorkerRecovery()
    func restarted(_ id: String, replacingContext: Bool) { events.append("restart") }
    func unregister(_ id: String) { events.append("cancel observers") }
}
enum Browsers { static func closePopups(of id: String) { events.append("popups") } }
enum ExtensionOffscreen { static func close(for id: String) { events.append("offscreen") } }
final class ExtensionCapture {
    static let shared = ExtensionCapture()
    func purge(_ id: String) { events.append("capture") }
}
enum ExtensionShims { static var awake = ["first": 42] }
func IOPMAssertionRelease(_ held: Int) { precondition(held == 42); events.append("keep awake") }
enum ExtensionNative { static func stopOrphans() { events.append("orphans") } }
enum DispatchQueue {
    struct Queue { func async(_ body: () -> Void) { body() } }
    static let main = Queue()
}
final class Extensions {
    let controller = Controller()
    var contexts = ["first": Context()]
    var nativePorts = ["first": Ports()]
    var actionsChanged = 0
'''
checks = r'''
}
for fail in [false, true] {
    for replacing in [false, true] {
        events = []
        ExtensionShims.awake = ["first": 42]
        let owner = Extensions()
        let port = owner.nativePorts["first"]!.allObjects[0]
        owner.controller.fail = fail
        let result = owner.unload("first", replacingContext: replacing)
        precondition(result == !fail, "Only successful unload allows revive")
        for required in ["unload", "host/socket cleanup", "disconnect", "popups", "offscreen", "capture", "keep awake", "orphans"] {
            precondition(events.filter { $0 == required }.count == 1, "Missing/duplicate cleanup: \(required), fail=\(fail)")
        }
        precondition(events.contains("restart") == !fail, "Failure must not claim restart")
        precondition(events.contains("cancel observers") == (replacing || fail))
        precondition(owner.contexts.isEmpty && owner.nativePorts.isEmpty && ExtensionShims.awake.isEmpty)
        precondition(port.isDisconnected && port.disconnectHandler == nil && owner.actionsChanged == 1)
        let before = events
        precondition(!owner.unload("first", replacingContext: replacing))
        precondition(events == before, "Repeated teardown cannot repeat cleanup")
        print("PASS extracted unload: throws=\(fail), replacingContext=\(replacing), unconditional cleanup and truthful result")
    }
}
'''
with tempfile.TemporaryDirectory(prefix='search-unload-review-') as folder:
    swift = pathlib.Path(folder) / 'main.swift'
    swift.write_text(stubs + method + checks)
    subprocess.run(['swift', str(swift)], check=True)
print('Source-extracted method with test doubles; not native WebKit fault injection.')
