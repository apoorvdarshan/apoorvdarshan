import { parseFragment } from 'parse5'
import { decodeHTML } from 'entities'

export const decodeEntities = (value = '') => decodeHTML(value)

// Extract text with an HTML parser. The returned string is text, not safe HTML;
// React renders it as text and generated HTML must use escapeHtml.
export function htmlText(value = '', imageAlt = alt => alt) {
  const visit = node => {
    if (node.nodeName === '#text') return node.value
    if (['script', 'style'].includes(node.tagName)) return ''
    if (node.tagName === 'img') return imageAlt(node.attrs.find(a => a.name === 'alt')?.value ?? '')
    return (node.childNodes ?? []).map(visit).join('')
  }
  return visit(parseFragment(value))
}
