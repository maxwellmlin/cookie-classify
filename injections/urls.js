/**
 * See: https://developer.mozilla.org/en-US/docs/Web/API/Document/links
 * @returns {string[]} Array of links
 */

var links = []

l = document.links;
for (var i = 0; i < l.length; i++) {
    links.push(l[i].href);
}

return links