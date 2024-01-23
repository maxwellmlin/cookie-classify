/**
 * Inject a groups field into the OneTrust `OptanonConsent` cookie to emulate varying levels of user cookie consent.
 * Currently, the script only disables tracking cookies (and enables all other cookies).
 * @return {res}
 */

/**
 * @typedef {Object} res
 * @property {boolean} success - Whether the injection was successful
 * @property {string} message - The injected groups field if successful, otherwise an error message
 */

/*
    js-cookie v3.0.5 | MIT 
    A simple, lightweight JavaScript API for handling browser cookies
    See: https://github.com/js-cookie/js-cookie
*/
!function(e,t){"object"==typeof exports&&"undefined"!=typeof module?module.exports=t():"function"==typeof define&&define.amd?define(t):(e="undefined"!=typeof globalThis?globalThis:e||self,function(){var n=e.Cookies,o=e.Cookies=t();o.noConflict=function(){return e.Cookies=n,o}}())}(this,(function(){"use strict";function e(e){for(var t=1;t<arguments.length;t++){var n=arguments[t];for(var o in n)e[o]=n[o]}return e}var t=function t(n,o){function r(t,r,i){if("undefined"!=typeof document){"number"==typeof(i=e({},o,i)).expires&&(i.expires=new Date(Date.now()+864e5*i.expires)),i.expires&&(i.expires=i.expires.toUTCString()),t=encodeURIComponent(t).replace(/%(2[346B]|5E|60|7C)/g,decodeURIComponent).replace(/[()]/g,escape);var c="";for(var u in i)i[u]&&(c+="; "+u,!0!==i[u]&&(c+="="+i[u].split(";")[0]));return document.cookie=t+"="+n.write(r,t)+c}}return Object.create({set:r,get:function(e){if("undefined"!=typeof document&&(!arguments.length||e)){for(var t=document.cookie?document.cookie.split("; "):[],o={},r=0;r<t.length;r++){var i=t[r].split("="),c=i.slice(1).join("=");try{var u=decodeURIComponent(i[0]);if(o[u]=n.read(c,u),e===u)break}catch(e){}}return e?o[e]:o}},remove:function(t,n){r(t,"",e({},n,{expires:-1}))},withAttributes:function(n){return t(this.converter,e({},this.attributes,n))},withConverter:function(n){return t(e({},this.converter,n),this.attributes)}},{attributes:{value:Object.freeze(o)},converter:{value:Object.freeze(n)}})}({read:function(e){return'"'===e[0]&&(e=e.slice(1,-1)),e.replace(/(%[\dA-F]{2})+/gi,decodeURIComponent)},write:function(e){return encodeURIComponent(e).replace(/%(2[346BF]|3[AC-F]|40|5[BDE]|60|7[BCD])/g,decodeURIComponent)}},{path:"/"});return t}));

/**
 * Retrieve a mapping of OneTrust Cookie Group IDs to their corresponding category names.
 * 
 * @returns {Object} - An object mapping OneTrust IDs to category names (e.g., {1: "Strictly Necessary Cookies"}). Returns null if no categories are found.
 */
function getCookieGroupIDs() {
    let categories = {} // Map OneTrust ID to category name (e.g. 1: "Strictly Necessary Cookies")

    const groups = OneTrust?.GetDomainData?.()?.Groups 
    if (groups === undefined) {
        return null
    }

    for (const group of groups) {
        const groupID = group.OptanonGroupId
        const groupName = group.GroupName
        if (groupID !== undefined && groupName !== undefined) {
            categories[groupID] = groupName
        }
    }

    if (Object.keys(categories).length === 0) {
        return null
    }

    return categories;
}


/**
 * Decode a query string into an object representation.
 * 
 * @param {string} str - The query string to be decoded.
 * @returns {Object} The decoded representation of the query string.
 */
function decodeString(str) {
    let keyValuePairs = str.split("&");
    let result = {};

    keyValuePairs.forEach(pair => {
        let [key, value] = pair.split("=");
        result[key] = value;
    });

    return result;
}

/**
 * Encode an object into a query string representation.
 * 
 * @param {Object} obj - The object to be encoded.
 * @returns {string} The encoded representation of the object.
 */
function encodeObject(obj) {
    let keyValuePairs = [];

    for (let key in obj) {
        if (obj.hasOwnProperty(key)) {
            keyValuePairs.push(`${key}=${obj[key]}`);
        }
    }

    return keyValuePairs.join("&");
}

/**
 * Encode a groups object into its string representation.
 * 
 * @param {Object} obj - The object to be encoded.
 * @returns {string} The encoded representation of the object (e.g., "C0004:0,C0003:1,C0002:1,C0001:1").
 */
function encodeGroups(obj) {
    let keyValuePairs = [];

    for (let key in obj) {
        if (obj.hasOwnProperty(key)) {
            keyValuePairs.push(`${key}:${obj[key]}`);
        }
    }

    return keyValuePairs.join(",");
}

/**
 * Generate an encoded groups string where only tracking cookies are disabled (and all other cookies are enabled).
 * 
 * @returns {string}
 */
function disableOnlyTracking() {
    cookieMapping = getCookieGroupIDs()

    // Any category that contains one of these words as a substring is considered a tracking category.
    // For example, "track" is a substring of "track", "tracking", and "tracker".
    trackingCorpus = ["track", "target", "advert"]

    // Any category that contains one of these words (exactly) is considered a tracking category.
    // We do this to avoid false positives.
    trackingCorpusExact = ["ad", "ads"]

    groupsObject = {}
    for (let id in cookieMapping) {
        if (cookieMapping.hasOwnProperty(id)) {
            tracking = false;

            category = cookieMapping[id].toLowerCase();

            category.split(" ").forEach(word => {
                if (trackingCorpusExact.includes(word)) {
                    tracking = true;
                }
            })

            for (word of trackingCorpus) {
                if (category.includes(word)) {
                    tracking = true;
                }
            }

            if (tracking) {
                groupsObject[id] = 0;
            } else {
                groupsObject[id] = 1;
            }
        }
    }

    return encodeGroups(groupsObject);
}

/**
 * Check whether we can execute the script.
 */
if (window.OneTrust === undefined) {
    msg = "OneTrust API not found."

    console.error(`ERROR: ${msg}`)
    return {
        "success": false,
        "message": msg
    }
}

let OptanonConsent = Cookies.get('OptanonConsent')
if (OptanonConsent === undefined) {
    msg = "OptanonConsent cookie not found."

    console.error(`ERROR: ${msg}`)
    return {
        "success": false,
        "message": msg
    }
}

let CookieGroupIDs = getCookieGroupIDs()
if (CookieGroupIDs === null) {
    msg = "No cookie categories found."

    console.error(`ERROR: ${msg}`)
    return {
        "success": false,
        "message": msg
    }
}

/**
 * Inject a groups field into the OptanonConsent cookie to disable only tracking cookies.
 */
OptanonConsentObject = decodeString(OptanonConsent)
OptanonConsentObject['groups'] = disableOnlyTracking()

console.log(`Injected groups field: ${OptanonConsentObject['groups']}`)

// These likely don't need to be updated but we do it anyway to fully emulate user interaction
OptanonConsentObject['interactionCount'] = (parseInt(OptanonConsentObject['interactionCount']) + 1).toString()
OptanonConsentObject['landingPath'] = "NotLandingPage"

// otBannerSdk.js uses this domain when setting cookies
if ((domain = OneTrust?.GetDomainData()?.Domain) === undefined) {
    msg = "OneTrust domain is undefined."

    console.error(`ERROR: ${msg}`)
    return {
        "success": false,
        "message": msg
    }
}
domain = `.${domain}`

Cookies.remove("OptanonConsent", { path: '/', domain: domain })
Cookies.set('OptanonConsent', encodeObject(OptanonConsentObject), { path: '/', domain: domain, expires: 1, secure: false, sameSite: 'Lax' })

// Close the OneTrust banner
Cookies.set('OptanonAlertBoxClosed', (new Date).toISOString(), { path: '/', domain: domain, expires: 1, secure: false, sameSite: 'Lax' })

return {
    "success": true,
    "message": OptanonConsentObject['groups']
}