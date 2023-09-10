DEBUG = false

/**
 * Return CSS selectors for clickable elements.
 * 
 * Clickable elements are defined as:
 * - <button> elements
 * - <a> elements
 * - Elements with an onclick attribute
 * - Elements with a pointer cursor style
 * 
 * Adapted from: https://gist.github.com/iiLaurens/81b1b47f6259485c93ce6f0cdd17490a
 * 
 * @returns {string[]} CSS selectors for clickable elements.
 */

var items = Array.prototype.slice.call(
    document.querySelectorAll('*')
).map(function (element) {
    return {
        element: element,
        include: (element.tagName === "BUTTON" || element.tagName === "A" || (element.onclick != null) || window.getComputedStyle(element).cursor == "pointer"),
    };
}).filter(item =>
    item.include);

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