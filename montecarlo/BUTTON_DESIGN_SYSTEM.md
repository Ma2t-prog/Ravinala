# GENESIX Button Design System v2.1

**Status**: ✅ IMPLEMENTED  
**Date**: March 21, 2026  
**Scope**: All buttons across GENESIX application  

---

## 🎯 Overview

The GENESIX button system has been completely redesigned to align with **Dark Luxe Quantitative** brand identity. All existing cyan-violet gradients have been eliminated. The new system features:

- **5 semantic button categories** (Primary, Premium, Secondary, Danger, Success)
- **Professional typography** (DM Sans, Geist family, 0.85rem minimum)
- **Elegant silver & gold palettes** (desaturated, institutional)
- **Touch-friendly sizing** (44px minimum height)
- **Smooth, snappy interactions** (200ms transitions)
- **Premium visual hierarchy** (subtle shadows, anti-aliasing, kerning)

---

## 📚 Button Categories

### 1. PRIMARY BUTTONS

**Use for**: Default actions, CTAs, standard form submissions

**Visual**: Silver gradient (subtle, professional)

```python
# In Streamlit:
st.button("Run Simulation")  # Automatically gets primary styling
st.button("Execute Trade")
st.button("Generate Report")
```

**CSS**:
```css
background: linear-gradient(
    135deg,
    rgba(192, 192, 200, 0.12) 0%,
    rgba(212, 212, 220, 0.18) 50%,
    rgba(192, 192, 200, 0.12) 100%
);
border: 1px solid rgba(192, 192, 210, 0.25);
color: #F0F0F5;
```

**Hover**: Silver glow, color brightens to #FFFFFF

---

### 2. PREMIUM BUTTONS

**Use for**: Hero CTA, premium products (Autocall, Reverse Convertible, etc.), flagship actions

**Visual**: Gold gradient (warm, luxurious)

```python
# In Streamlit (add class):
st.markdown(
    '<button class="btn-premium">Autocall</button>',
    unsafe_allow_html=True
)
```

Or use custom HTML with st.markdown:

```html
<button class="btn-premium">Reverse Convertible</button>
```

**CSS**:
```css
background: linear-gradient(
    135deg,
    rgba(212, 175, 55, 0.08) 0%,
    rgba(212, 175, 55, 0.14) 40%,
    rgba(192, 168, 80, 0.10) 100%
);
border: 1px solid rgba(212, 175, 55, 0.25);
color: #F0ECE0;
```

**Hover**: Gold glow intensifies, color brightens to #FFFFFF

---

### 3. SECONDARY BUTTONS

**Use for**: Cancel, Back, Reset, companion actions

**Visual**: Ghost style (transparent background, minimal)

```python
st.button("Cancel", key="cancel_btn")
st.button("Back")
```

**CSS**:
```css
background: transparent;
border: 1px solid rgba(255, 255, 255, 0.10);
color: #B8B8C8;
```

**Hover**: Light background fills (4% opacity)

---

### 4. DANGER BUTTONS

**Use for**: Delete, Close Position, Destructive actions

**Visual**: Red-tinted (alert but not aggressive)

```python
# Custom HTML:
st.markdown(
    '<button class="btn-danger">Delete Portfolio</button>',
    unsafe_help=True
)
```

**CSS**:
```css
background: rgba(255, 82, 82, 0.08);
border: 1px solid rgba(255, 82, 82, 0.25);
color: #FF8A80;
```

**Hover**: Red glow, color brightens to #FF5252

---

### 5. SUCCESS BUTTONS

**Use for**: Confirm Trade, Save, Apply Changes

**Visual**: Green-tinted (positive, affirming)

```python
st.markdown(
    '<button class="btn-success">Confirm Trade</button>',
    unsafe_html=True
)
```

**CSS**:
```css
background: rgba(0, 230, 118, 0.08);
border: 1px solid rgba(0, 230, 118, 0.25);
color: #69F0AE;
```

**Hover**: Green glow, color brightens to #00E676

---

## 🔧 Implementation Guide

### Option A: Streamlit's Default Button (Recommended)

```python
import streamlit as st
from src.genesix.design_system import apply_quantum_dark

# At page top:
st.set_page_config(...)
apply_quantum_dark()  # Applies button styling automatically

# Buttons now have premium silver styling:
if st.button("Run Backtest"):
    # Action
    pass
```

**Auto-applied to**:
- `st.button()`
- `st.form_submit_button()`
- All `.stButton > button` elements

---

### Option B: Custom HTML (For Premium/Special Buttons)

```python
import streamlit as st

# Premium gold button:
st.markdown(
    """
    <button class="btn-premium">₩ Structured Products</button>
    """,
    unsafe_html=True
)

# Danger button:
st.markdown(
    """
    <button class="btn-danger">Delete Strategy</button>
    """,
    unsafe_html=True
)

# Success button:
st.markdown(
    """
    <button class="btn-success">Confirm Order</button>
    """,
    unsafe_html=True
)
```

---

### Option C: Custom Components (If Using HTML Forms)

```html
<!-- Primary (default) -->
<button class="btn btn-primary">Click Me</button>

<!-- Premium/Gold -->
<button class="btn btn-premium">Premium Action</button>

<!-- Secondary -->
<button class="btn btn-secondary">Cancel</button>

<!-- Danger -->
<button class="btn btn-danger">Delete</button>

<!-- Success -->
<button class="btn btn-success">Confirm</button>

<!-- Compact (for toolbars) -->
<button class="btn btn-compact">Filter</button>

<!-- Pill/Tag -->
<button class="btn-pill">ETF</button>
<button class="btn-pill selected">Stocks</button>

<!-- Button Group -->
<div class="btn-group">
    <button class="btn-group-item active">This Month</button>
    <button class="btn-group-item">Last Month</button>
    <button class="btn-group-item">YTD</button>
</div>
```

---

## 📐 Universal Typography Rules

These rules apply to **ALL buttons** without exception:

```css
/* Font Family */
font-family: 'DM Sans', 'Geist', -apple-system, BlinkMacSystemFont, sans-serif;

/* Size — MINIMUM 0.85rem (13.6px) */
font-size: 0.9rem;      /* Standard buttons */
font-size: 0.85rem;     /* Compact buttons */
font-size: 1rem;        /* Hero CTAs */

/* Weight — ALWAYS 500+ */
font-weight: 500;       /* Medium — standard */
font-weight: 600;       /* Semibold — emphasis */

/* Spacing */
letter-spacing: 0.02em;  /* Breathing room */
padding: 12px 24px;      /* Minimum: 10px 20px */
min-height: 44px;        /* Touch-friendly */

/* Smoothing */
-webkit-font-smoothing: antialiased;
-moz-osx-font-smoothing: grayscale;

/* Interactions */
transition: all 200ms cubic-bezier(0.25, 0.46, 0.45, 0.94);
cursor: pointer;

/* Rounding */
border-radius: 8px to 12px;
```

---

## 🎨 Color Palette Reference

| Category | Background | Border | Text | Hover Text |
|----------|-----------|--------|------|-----------|
| PRIMARY (Silver) | rgba(192,192,200, 0.12-0.18) | rgba(192,192,210, 0.25-0.40) | #F0F0F5 | #FFFFFF |
| PREMIUM (Gold) | rgba(212,175,55, 0.08-0.14) | rgba(212,175,55, 0.25-0.45) | #F0ECE0 | #FFFFFF |
| SECONDARY | transparent | rgba(255,255,255, 0.10-0.20) | #B8B8C8 | #E0E0F0 |
| DANGER (Red) | rgba(255,82,82, 0.08-0.14) | rgba(255,82,82, 0.25-0.40) | #FF8A80 | #FF5252 |
| SUCCESS (Green) | rgba(0,230,118, 0.08-0.14) | rgba(0,230,118, 0.25-0.40) | #69F0AE | #00E676 |

---

## 🚫 Absolute No-Go List

### Forbidden Colors
- ❌ `#00BFFF` (cyan electric)
- ❌ `#8A2BE2` (violet)
- ❌ `#FF00FF` (magenta)
- ❌ `#00FF00` (lime)
- ❌ Any `cyan → violet` gradient
- ❌ Any `blue → pink` gradient
- ❌ Colors with 100% saturation

### Forbidden Typography
- ❌ `font-weight: 300` or `400` alone
- ❌ `font-size` < 0.8rem (unless badge)
- ❌ System font without fallback
- ❌ `letter-spacing: 0`
- ❌ White text on saturated background

### Forbidden Effects
- ❌ `box-shadow` spread > 20px
- ❌ `text-shadow` on buttons
- ❌ `backdrop-filter: blur()` on buttons
- ❌ Animations > 300ms on hover
- ❌ `transform: scale()` > 1.05

---

## ✅ Implementation Checklist

Before deploying any button, verify:

- [ ] Font is DM Sans or Geist (not system default)
- [ ] Size ≥ 0.85rem
- [ ] Font-weight ≥ 500
- [ ] Letter-spacing ≥ 0.02em
- [ ] Padding ≥ 10px 20px
- [ ] Min-height ≥ 40px
- [ ] Border-radius 8-12px
- [ ] NO cyan, violet, or pure colors
- [ ] Background uses desaturated rgba (not solid)
- [ ] Border is thin (1px) and semi-transparent
- [ ] Hover change is subtle but visible
- [ ] Text is instantly readable (no eye strain)
- [ ] Button has clear semantic category
- [ ] Anti-aliasing enabled
- [ ] No `text-transform: uppercase` on long text

---

## 🔍 Quality Assurance

### Testing Checklist

Test each button:
1. **Visual**: Does it match one of the 5 categories?
2. **Typography**: Can you read it instantly without strain?
3. **Interaction**: Is hover smooth and not jarring?
4. **Accessibility**: Is color contrast sufficient? (WCAG AA minimum)
5. **Performance**: No animation jank?
6. **Consistency**: Does it match the design system palette?

### Browser Testing
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)
- [ ] Mobile Safari
- [ ] Chrome Android

---

## 📋 Files Modified

| File | Change | Status |
|------|--------|--------|
| `src/genesix/design_system/__init__.py` | Added complete button design system with 5 categories + variants | ✅ |
| `src/_shared.py` | Replaced cyan-violet gradient with professional silver system | ✅ |
| `src/auth/auth_ui.py` | Updated auth buttons to premium gold system | ✅ |

---

## 🚀 Rollout Plan

### Phase 1: Core System (DONE)
- [x] Update design_system/__init__.py
- [x] Update _shared.py (main button styles)
- [x] Update auth_ui.py (auth screens)

### Phase 2: Audit & Apply (TODO)
- [ ] Search codebase for all `st.button()` uses
- [ ] Verify all buttons follow new system
- [ ] Test all pages visually
- [ ] Update any custom button components

### Phase 3: Documentation (DONE)
- [x] Create this guide
- [x] Add button category reference
- [x] Include implementation examples

---

## 📞 Support & Questions

If you need to add a new button type:

1. Check if it fits into the 5 categories (Primary, Premium, Secondary, Danger, Success)
2. Use the corresponding CSS class
3. Verify against the checklist
4. If creating a new category, contact design team

---

## 🎨 Design System Tokens

For future reference, key design tokens:

```python
# Silver (Primary)
silver_gradient_start = "rgba(192, 192, 200, 0.12)"
silver_gradient_mid = "rgba(212, 212, 220, 0.18)"
silver_border = "rgba(192, 192, 210, 0.25)"
silver_text = "#F0F0F5"

# Gold (Premium)
gold_gradient_start = "rgba(212, 175, 55, 0.08)"
gold_gradient_mid = "rgba(212, 175, 55, 0.14)"
gold_border = "rgba(212, 175, 55, 0.25)"
gold_text = "#F0ECE0"

# Semantic colors
danger_color = "#FF5252"
success_color = "#00E676"
warning_color = "#FFD740"

# Typography
font_family = "'DM Sans', 'Geist', -apple-system"
font_size_standard = "0.9rem"
font_weight_standard = "500"
letter_spacing = "0.02em"

# Dimensions
button_padding = "12px 24px"
button_min_height = "44px"
border_radius = "10px"

# Animation
transition = "all 200ms cubic-bezier(0.25, 0.46, 0.45, 0.94)"
```

---

**Version**: 2.1  
**Last Updated**: March 21, 2026  
**Maintained by**: GENESIX Design Team  
