# Apple Notes HTML Formatting Support

Based on comprehensive testing with the formatting test note, here's what Apple Notes supports.

**Note:** PDF exports from Apple Notes do NOT preserve visual formatting (colors, fonts, styles), but the actual notes in Apple Notes preserve all formatting correctly.

## ✅ **CONFIRMED WORKING**

### Text Formatting
- **Bold** (`<strong>`): ✅ Text appears bold
- **Italic** (`<em>`): ✅ Text appears italic
- **Underline** (`<u>`): ✅ Text appears underlined
- **Strikethrough** (`<s>`): ✅ Text appears struck through
- **Combinations**: ✅ Bold+italic, bold+italic+underline all work

### Font Styling
- **Font Sizes** (`font-size:10px` to `32px`): ✅ All sizes work correctly
- **Font Families** (`font-family:Arial`, `Times New Roman`, `Courier`, `Helvetica`, `Verdana`, `Georgia`): ✅ All fonts render correctly
- **Colors** (`color:red`, `color:#FF0000`, etc.): ✅ Text colors work (red, blue, green, purple, orange, hex codes)
- **Background Colors** (`background-color:yellow`, etc.): ✅ Background colors work
- **Color Combinations**: ✅ White on black, blue on light yellow, etc. all work

### Text Alignment
- **Left** (`text-align:left`): ✅ Default alignment
- **Center** (`text-align:center`): ✅ Text centers correctly
- **Right** (`text-align:right`): ✅ Text aligns right
- **Justify** (`text-align:justify`): ✅ Text is justified across full width

### Structural Elements
- **Lists (Unordered)**: ✅ Bullet points (●) are preserved
- **Lists (Ordered)**: ✅ Numbered lists (1., 2., 3.) are preserved
- **Nested Lists**: ✅ Both nested unordered and ordered lists work
- **Headings**: ✅ H1-H6 headings work with proper hierarchy (H1 largest, H6 smallest)
- **Paragraphs**: ✅ Multiple `<p>` tags work (each line as separate paragraph)
- **Line Breaks**: ✅ Using separate `<p>` tags preserves line breaks

### Links
- **Links** (`<a href="...">`): ✅ Links are clickable (blue and underlined)
- **Styled Links**: ✅ Link styling is preserved (bold, colors, etc.)

### Tables
- **Basic Tables**: ✅ Table structure is preserved
- **Table Headers**: ✅ Header rows are preserved
- **Table Cells**: ✅ Cell content is preserved
- **Styled Cells**: ✅ Background colors, text colors, and bold work in cells

### Code and Preformatted Text
- **Inline Code** (`<code>`): ✅ Monospace font with distinct styling
- **Preformatted Blocks** (`<pre>`): ✅ Multi-line code blocks with gray background

### Advanced Elements
- **Horizontal Rules** (`<hr>`): ✅ Horizontal lines appear
- **Span Elements** (`<span style="...">`): ✅ Inline styling works (colors, backgrounds, bold)
- **Complex Combinations**: ✅ Multiple styles together work (e.g., blue, large, bold, centered text)

### Text Content
- **Emojis**: ✅ All emojis display correctly (😀 🎉 ✅ ❌ ⚠️ 🚀 💡 📝)
- **Special Characters**: ✅ Symbols (©, ®, ™, €, £, ¥, §, ¶) work
- **Math Symbols**: ✅ (∑, ∏, ∫, √, ∞, ≈, ≠, ≤, ≥) work
- **Unicode**: ✅ Multiple languages (Chinese, Japanese, Korean, Arabic, Russian) work
- **Quotes**: ✅ Various quote styles work ("Double quotes", 'Single quotes', «Guillemets»)

## ❌ **CONFIRMED NOT WORKING**

- **`<br>` tags**: Single `<br>` tags are ignored (we work around this by using separate `<p>` tags)
- **Blockquotes** (`<blockquote>`): Not rendered; text may appear without indentation or styling

## Current Implementation Strategy

The `convert_body_to_html` function in `applescript.py`:
1. Splits text by double newlines (`\n\n`) to identify paragraphs
2. Within each paragraph, splits by single newlines (`\n`)
3. Makes each line its own `<p>` tag to preserve line breaks (since `<br>` doesn't work)
4. Preserves blank lines as empty `<p></p>` tags

## Summary

Apple Notes has **excellent HTML formatting support**! Almost all standard HTML formatting works:
- ✅ Text formatting (bold, italic, underline, strikethrough)
- ✅ Font sizes and families
- ✅ Colors (text and background)
- ✅ Text alignment
- ✅ Lists (ordered, unordered, nested)
- ✅ Links (clickable)
- ✅ Tables
- ✅ Code blocks
- ✅ Horizontal rules
- ✅ Headings
- ✅ Complex style combinations
- ✅ Emojis and special characters

The only limitation is that `<br>` tags don't work, but we work around this by using separate `<p>` tags for each line.

**Note:** PDF exports from Apple Notes strip all visual formatting, so the actual notes look much better than PDF exports suggest.

---

## HTML Embedding

The API accepts **HTML in the note body**. If the body starts with `<` and contains `>` (i.e. looks like HTML), it is passed through to Apple Notes as-is. Otherwise, plain text is converted to HTML (line breaks become separate paragraphs).

**For Custom GPT / browser-based clients:** Send HTML in the `body` field to get rich formatting (bold, lists, links, tables, etc.). See `CUSTOM_GPT_CONFIG.md` for instructions.
