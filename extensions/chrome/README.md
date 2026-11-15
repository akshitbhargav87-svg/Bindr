# Bindr explicit Chrome capture

Manifest V3 source; not installed or published by this implementation.

The popup reads only a deliberate selection or takes the visible screenshot after the user presses its corresponding button. It shows an editable text/image preview. The user can keep the reviewed result as a local file and upload it through authenticated Bindr capture. There is no background/content-script monitoring, broad host permission, cookie access, long-lived credential copy or automatic submission.

Authenticated pairing/submission stays disabled until A provides a versioned short-lived pairing contract. An unpaired extension cannot list/read cases. The current working fallback is explicit reviewed-file capture; it does not claim a connected upload.

For developer inspection, a human may load this directory as an unpacked extension through Chrome's extensions page. No automated extension installation or permissions change was performed. Test selected text, a restricted page failure, screenshot preview and the local-file fallback before advertising support; Chrome Web Store distribution has not been attempted.

Current guidance checked 15 November 2026: [activeTab](https://developer.chrome.com/docs/extensions/develop/concepts/activeTab), [captureVisibleTab](https://developer.chrome.com/docs/extensions/reference/api/tabs#method-captureVisibleTab).
