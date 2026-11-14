# Landing asset provenance

All runtime images and fonts are served locally. No image proxy, external image request or font CDN is required by the landing page.

## Typography

- Nunito 800/900: @fontsource/nunito, self-hosted package; rounded marketing headings only. Font licensing is included in the dependency package.
- Inter 400/500/600: @fontsource/inter for readable body text and controls.
- IBM Plex Mono 400: @fontsource/ibm-plex-mono, kept for product identifiers.
- This marketing type revision follows Tushar's later approval of the consumer SVG proposal; it supersedes the earlier marketing heading sizes/Inter-only instruction.

## Photograph

`public/media/everyday-phone.jpg`: Priscilla Du Preez, “woman sits on sidewalk holding smartphone while smiling.”

- Source: https://unsplash.com/photos/woman-sits-on-sidewalk-holding-smartphone-while-smiling-zH1Mqf6ojwU
- File: https://images.unsplash.com/photo-1522010496643-e5dbf53b7338?auto=format&fit=crop&w=1000&q=85
- Source page marks it free under the Unsplash License: https://unsplash.com/license
- Used as lifestyle photography, not a customer, testimonial, support agent or endorsement. The subject is not named in the product UI; the on-image stock caption was removed following visual review.
- Original JPEG downloaded at 1000px wide, 128,611 bytes. CSS crops it responsively. Photographer credit is retained here.

## Brand marks

Simple Icons source: https://github.com/simple-icons/simple-icons, CC0 icon collection. Brand trademarks remain with their respective owners. These are sourced logo shapes, not custom imitations or claimed official partnerships.

- Flipkart: https://raw.githubusercontent.com/simple-icons/simple-icons/12.0.0/icons/flipkart.svg
- Swiggy: https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/swiggy.svg
- Uber: https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/uber.svg
- Zomato: https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/zomato.svg

Shapes are preserved; single fills set to brand colors. Downloaded copies are versioned locally, so runtime behavior does not depend on the upstream develop branch. The company strip explicitly labels illustrative examples and states that Bindr is independent and unaffiliated. Following visual review, landing message/evidence artwork uses Flipkart's real logo, with “Refund example” in the preview breadcrumb. That conversation is a sample scenario, not a real customer communication or verified transaction. The privacy note retains that context. NovaMart remains in the synthetic mock adapter fixtures.

## Original assets

Bindr logo supplied by Tushar; original PNG and vector redraw retained in public/. Message cards, source highlights, workflow scenes and closing document artwork are original HTML/CSS/SVG compositions. Reference screenshots and the preview-generation scripts are not runtime assets. design-previews/ is ignored so manual staging does not include those local design artifacts.
