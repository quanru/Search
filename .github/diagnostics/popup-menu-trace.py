#!/usr/bin/env python3
"""Apply scoped, test-only popup event tracing to a 14d6949 checkout.

This derivative is diagnostic, not an exact-head validation. No popup
permission or hidden-screen guard is changed. Run only in the isolated
verification checkout, then build and run Tests/link_menu.py.
"""
from pathlib import Path


def replace(path, old, new):
    file = Path(path)
    source = file.read_text()
    assert source.count(old) == 1, (path, old[:70], source.count(old))
    file.write_text(source.replace(old, new, 1))

replace('Sources/Search/Tab.swift',
'''    var onMenuClosed: (() -> Void)?
''',
'''    var onMenuClosed: (() -> Void)?
    var popupTrace: [String] = []
    func tracePopup(_ text: String) {
        guard Store.testing, popupTrace.count < 80 else { return }
        popupTrace.append("\\(ProcessInfo.processInfo.systemUptime): \\(text)")
    }
''')
replace('Sources/Search/Tab.swift',
'''    override func didCloseMenu(_ menu: NSMenu, with event: NSEvent?) {
        super.didCloseMenu''',
'''    override func didCloseMenu(_ menu: NSMenu, with event: NSEvent?) {
        tracePopup("didCloseMenu")
        super.didCloseMenu''')
replace('Sources/Search/Tab.swift',
'''    override func willOpenMenu(_ menu: NSMenu, with event: NSEvent) {
        super.willOpenMenu''',
'''    override func willOpenMenu(_ menu: NSMenu, with event: NSEvent) {
        tracePopup("willOpenMenu")
        super.willOpenMenu''')
replace('Sources/Search/Tab.swift',
'''    @objc private func openLinkBehind(_ item: NSMenuItem) {
        guard let action''',
'''    @objc private func openLinkBehind(_ item: NSMenuItem) {
        tracePopup("background menu action")
        guard let action''')
replace('Sources/Search/PopupGesture.swift',
'''            tab.popupGesture.record(origin: PopupGesture.origin(message.frameInfo), kind: kind)''',
'''            (message.webView as? PageView)?.tracePopup("record \\(kind), main=\\(message.frameInfo.isMainFrame)")
            tab.popupGesture.record(origin: PopupGesture.origin(message.frameInfo), kind: kind)''')
replace('Sources/Search/Browser.swift',
'''        guard let opener = popupTab(for: webView),
              opener.popupGesture.take(origin: PopupGesture.origin(action.sourceFrame), mainFrame: action.sourceFrame.isMainFrame) else { return nil }''',
'''        guard let opener = popupTab(for: webView) else {
            (webView as? PageView)?.tracePopup("popup owner missing")
            return nil
        }
        let allowed = opener.popupGesture.take(origin: PopupGesture.origin(action.sourceFrame), mainFrame: action.sourceFrame.isMainFrame)
        (webView as? PageView)?.tracePopup("take=\\(allowed), main=\\(action.sourceFrame.isMainFrame), type=\\(action.navigationType.rawValue)")
        guard allowed else { return nil }''')
replace('Sources/Search/Bench.swift',
'''            PageView.picking = pick
            PageView.pickingDelay = delay''',
'''            web.popupTrace = []
            web.tracePopup("linkmenu command, delay=\\(delay)")
            PageView.picking = pick
            PageView.pickingDelay = delay''')
replace('Sources/Search/Bench.swift',
'''                    "urls": browser.tabs.map { $0.address?.absoluteString ?? "" },
                    "active":''',
'''                    "urls": browser.tabs.map { $0.address?.absoluteString ?? "" },
                    "popupTrace": web.popupTrace,
                    "active":''')
replace('Tests/link_menu.py',
'''        r = menu(a, ("Open Link in New Tab", "behind"))''',
'''        r = menu(a, ("Open Link in New Tab", "behind"))
        print("background trace", r, flush=True)''')
replace('Tests/link_menu.py',
'''        r = menu(a, ("Open Link in New Tab and Go to It", "front"))''',
'''        r = menu(a, ("Open Link in New Tab and Go to It", "front"))
        print("foreground trace", r, flush=True)''')
print("Applied diagnostic tracing only; grant and isolation policy unchanged.")

replace('Sources/Search/PopupGesture.swift',
'''    mutating func clear() { self = PopupGesture() }''',
'''    var traceState: String {
        "recorded=\\(recorded), consumed=\\(consumed), menu=\\(menu), age=\\(ProcessInfo.processInfo.systemUptime - time), origin=\\(origin ?? "opaque")"
    }
    mutating func clear() { self = PopupGesture() }''')
replace('Sources/Search/Browser.swift',
'''                self?.popupTab(for: webView)?.popupGesture.clear()''',
'''                (webView as? PageView)?.tracePopup("allowed main-frame navigation clears grant")
                self?.popupTab(for: webView)?.popupGesture.clear()''')
replace('Sources/Search/Browser.swift',
'''        let allowed = opener.popupGesture.take(origin: PopupGesture.origin(action.sourceFrame), mainFrame: action.sourceFrame.isMainFrame)''',
'''        (webView as? PageView)?.tracePopup("before take: \\(opener.popupGesture.traceState)")
        let allowed = opener.popupGesture.take(origin: PopupGesture.origin(action.sourceFrame), mainFrame: action.sourceFrame.isMainFrame)''')
