DEBUG = false

/**
 * Return CSS selectors for clickable elements.
 * 
 * Clickable elements are defined as:
 * 
 * Adapted from: https://gist.github.com/iiLaurens/81b1b47f6259485c93ce6f0cdd17490a
 * 
 * @returns {Object|null} - An object mapping OneTrust IDs to category names (e.g., {1: "Strictly Necessary Cookies"}).
 *                          If there's a conflict in IDs, it returns null.
 */

window.scrollTo(0, 0)
var bodyRect = document.body.getBoundingClientRect();

var items = Array.prototype.slice.call(
    document.querySelectorAll('*')
).map(function (element) {
    var rect = element.getBoundingClientRect();
    return {
        element: element,
        include: (element.tagName === "BUTTON" || element.tagName === "A" || (element.onclick != null) || window.getComputedStyle(element).cursor == "pointer"),
        rect: {
            left: Math.max(rect.left - bodyRect.x, 0),
            top: Math.max(rect.top - bodyRect.y, 0),
            right: Math.min(rect.right - bodyRect.x, document.body.clientWidth),
            bottom: Math.min(rect.bottom - bodyRect.y, document.body.clientHeight)
        },
        text: element.textContent.trim().replace(/\s{2,}/g, ' ')
    };
}).filter(item =>
    item.include);

// Only keep inner clickable items
// items = items.filter(x => !items.some(y => x.element.contains(y.element) && !(x == y)))

if (debug) {
    // Lets create a floating border on top of these elements that will always be visible
    items.forEach(function (item) {
        newElement = document.createElement("div");
        newElement.style.outline = "2px dashed rgba(255,0,0,.75)";
        newElement.style.position = "absolute";
        newElement.style.left = item.rect.left + "px";
        newElement.style.top = item.rect.top + "px";
        newElement.style.width = (item.rect.right - item.rect.left) + "px";
        newElement.style.height = (item.rect.bottom - item.rect.top) + "px";
        newElement.style.pointerEvents = "none";
        newElement.style.boxSizering = "border-box";
        newElement.style.zIndex = 2147483647;
        document.body.appendChild(newElement);
    })
}

// See: https://stackoverflow.com/a/4588211
function fullPath(el) {
    var names = [];
    while (el.parentNode) {
        if (el.id) {
            names.unshift('#' + el.id);
            break;
        } else {
            if (el == el.ownerDocument.documentElement) names.unshift(el.tagName);
            else {
                for (var c = 1, e = el; e.previousElementSibling; e = e.previousElementSibling, c++);
                names.unshift(el.tagName + ":nth-child(" + c + ")");
            }
            el = el.parentNode;
        }
    }
    return names.join(" > ");
}

selectors = []
for (item of items) {
    selectors.push(fullPath(item.element))
}

return selectors