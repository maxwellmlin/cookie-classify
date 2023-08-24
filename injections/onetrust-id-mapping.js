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
    console.log(categories)
}