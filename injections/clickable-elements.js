DEBUG = false

/**
 * Return CSS selectors and types for clickable elements.
 * 
 * Clickable elements have the following types:
 * - "button": <button> elements
 * - "link": <a> elements
 * - "onclick": Elements with an onclick attribute
 * - "pointer": Elements with a pointer cursor style
 * The first matching type is used. (Types get more general from top to bottom.)
 * 
 * Adapted from: https://gist.github.com/iiLaurens/81b1b47f6259485c93ce6f0cdd17490a
 * 
 * @returns {string[], string[]} CSS selectors, types for clickable elements.
 */

var items = Array.prototype.slice.call(
    document.querySelectorAll('*')
).map(function (element) {
    return {
        element: element,
        include: (element.tagName === "BUTTON" || element.tagName === "A" || (element.onclick != null) || window.getComputedStyle(element).cursor == "pointer"),
        type: determineType(element),
    };
}).filter(item =>
    item.include);


function determineType(element) {
    if (element.tagName === "BUTTON") {
        return "button";
    }
    if (element.tagName === "A") {
        return "link";
    }
    if (element.onclick != null) {
        return "onclick";
    }
    if (window.getComputedStyle(element).cursor == "pointer") {
        return "pointer";
    }
    return null; // In case none of the conditions match
}

// See: https://stackoverflow.com/a/4588211
function fullPath(el) {
    var names = [];
    while (el.parentNode) {
        if (el == el.ownerDocument.documentElement) names.unshift(el.tagName);
        else {
            for (var c = 1, e = el; e.previousElementSibling; e = e.previousElementSibling, c++);
            names.unshift(el.tagName + ":nth-child(" + c + ")");
        }
        el = el.parentNode;
    }
    return names.join(" > ");
}

selectors = []
types = []
for (item of items) {
    selectors.push(fullPath(item.element))
    types.push(item.type)
}

return [selectors, types]