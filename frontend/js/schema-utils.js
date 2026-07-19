function websiteSchema() {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "VigyanLLM",
    "url": "https://www.vigyanllm.in",
    "description": "AI-powered bioinformatics tools for primer design, BLAST search, and multiple sequence alignment.",
    "publisher": {
      "@type": "Organization",
      "name": "VigyanLLM Private Limited",
      "url": "https://www.vigyanllm.in/about"
    },
    "potentialAction": {
      "@type": "SearchAction",
      "target": "https://www.vigyanllm.in/search?q={search_term_string}",
      "query-input": "required name=search_term_string"
    }
  }
}

function toolSchema(pagePath, toolName, description) {
  return {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "name": toolName,
    "url": "https://www.vigyanllm.in" + pagePath,
    "description": description,
    "applicationCategory": "BiotechnologyApplication",
    "operatingSystem": "Web Browser",
    "offers": {
      "@type": "Offer",
      "price": "0",
      "priceCurrency": "USD",
      "description": "Free tier available"
    },
    "creator": {
      "@type": "Organization",
      "name": "VigyanLLM Private Limited"
    }
  }
}

function articleSchema(slug, title, description, datePublished, dateModified) {
  return {
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": title.substring(0, 110),
    "description": description,
    "url": "https://www.vigyanllm.in/blog/" + slug,
    "mainEntityOfPage": "https://www.vigyanllm.in/blog/" + slug,
    "author": {
      "@type": "Organization",
      "name": "VigyanLLM Private Limited",
      "url": "https://www.vigyanllm.in/about"
    },
    "publisher": {
      "@type": "Organization",
      "name": "VigyanLLM Private Limited",
      "logo": {
        "@type": "ImageObject",
        "url": "https://www.vigyanllm.in/logo.png"
      }
    },
    "datePublished": datePublished,
    "dateModified": dateModified || datePublished
  }
}

function breadcrumbSchema(pathSegments) {
  const baseUrl = "https://www.vigyanllm.in"
  const items = [
    { "@type": "ListItem", "position": 1, "name": "Home", "item": baseUrl }
  ]
  pathSegments.forEach(function(seg, i) {
    var item = { "@type": "ListItem", "position": i + 2, "name": seg.name }
    if (seg.url) item.item = baseUrl + seg.url
    items.push(item)
  })
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": items
  }
}

function injectSchema(schemaObj) {
  var script = document.createElement('script')
  script.type = 'application/ld+json'
  script.textContent = JSON.stringify(schemaObj)
  document.head.appendChild(script)
}

function schemaTag(schemaObj) {
  return '<script type="application/ld+json">' + JSON.stringify(schemaObj) + '<\/script>'
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    websiteSchema: websiteSchema,
    toolSchema: toolSchema,
    articleSchema: articleSchema,
    breadcrumbSchema: breadcrumbSchema,
    injectSchema: injectSchema,
    schemaTag: schemaTag
  }
}
