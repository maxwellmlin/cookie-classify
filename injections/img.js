/**
 * @returns {string[]} Array of img hrefs
 */

return Array.from(document.getElementsByTagName("img")).map(i => i.src);
