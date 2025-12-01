var zWatcherID = null;
const target = "ChangeMe.epub";

// This function runs when Zotero starts or the plugin is enabled
function startup({ id, version, rootURI }) {
    // Register the observer
    zWatcherID = Zotero.Notifier.registerObserver({
        notify: (e, t, ids) => {
            if (e === 'add' || e === 'modify') {
                run(ids);
            }
        }
    }, ['item']);
    
    console.log("Epub Fixer: Started");
}

// This function runs when Zotero closes or the plugin is disabled
function shutdown() {
    if (zWatcherID) {
        Zotero.Notifier.unregisterObserver(zWatcherID);
        zWatcherID = null;
    }
    console.log("Epub Fixer: Stopped");
}

function install() {}
function uninstall() {}

// Your main logic, slightly adapted for Plugin scope
const run = async (ids) => {
    if (!ids?.length) return;
    const items = await Zotero.Items.get(ids);
    
    for (const item of items) {
        if (!item.isAttachment()) continue;
        const matches = item.getField('title') === target || item.attachmentFilename === target;
        if (!matches) continue;

        if (item.parentID) {
            // Case 1: Has a parent, fix the title
            const parent = Zotero.Items.get(item.parentID);
            if (parent && item.getField('title') !== parent.getField('title')) {
                item.setField('title', parent.getField('title'));
                await item.saveTx();
            }
        } else {
            // Case 2: No parent, select it in the UI
            // In a plugin, we must find the main window to interact with the UI
            const win = Zotero.getMainWindow();
            if (win && win.ZoteroPane) {
                const zp = win.ZoteroPane;
                zp.selectItems ? await zp.selectItems([item.id]) : await zp.selectItem(item.id);
                // "recognizeSelected" isn't always needed or available in all versions, 
                // but selectItem usually does the job of highlighting.
                if (win.focus) win.focus();
            }
        }
    }
};
