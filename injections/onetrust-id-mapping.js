/**
 * NOTE: This code is no longer useful since we can directly access the desired mapping via the JS OneTrust API.
 * 
 * Retrieve a mapping of OneTrust Cookie Group IDs to their corresponding category names.
 * 
 * The function scans the document for elements with IDs that start with 'ot-header-id-' and 
 * extracts the unique ID part, mapping it to the element's inner text (expected to be the category name).
 * 
 * In case of conflicts where the same OneTrust ID maps to multiple categories, it logs a warning 
 * showing the conflicting elements and returns null.
 * 
 * @returns {Object|null} - An object mapping OneTrust IDs to category names (e.g., {1: "Strictly Necessary Cookies"}).
 *                          If there's a conflict in IDs, it returns null.
 */
function getCookieGroupIDsWithHTML() {
    // Select all elements with an ID that starts with 'ot-header-id-'
    onetrust_id_elements = document.querySelectorAll('*[id^="ot-header-id-"]');

    success = true;
    categories = {} // Map OneTrust ID to category name (e.g. 1: "Strictly Necessary Cookies")
    onetrust_id_elements.forEach(function (element) {
        let onetrust_id = element.id.split('ot-header-id-')[1];  // get the ID after the prefix
        let category = element.innerText;

        // Check for conflicts
        if (onetrust_id in categories && categories[onetrust_id] !== category) {
            let duplicate_id_elements = document.querySelectorAll(`*[id^="ot-header-id-${onetrust_id}"]`)
            console.warn(`The same OneTrust ID maps to different categories! Conflicting elements are:`);
            console.warn(duplicate_id_elements);

            success = false;
        }

        categories[onetrust_id] = category;
    });

    if (success) {
        return categories;
    } else {
        return null;
    }
}

getCookieGroupIDsWithHTML()