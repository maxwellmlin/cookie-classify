/**
 * Return the CMP(s) used on the page.
 * @returns {string[]} An array of API names that are exposed on the `window` object. May be empty.
 */

possibleAPIs = ["OneTrust", "__tcfapi"];

activeAPIs = [];
for (let name of possibleAPIs) {
  if (!!window[name]) {
    activeAPIs.push(name);
  }
}

return activeAPIs;