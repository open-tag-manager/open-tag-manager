# Collect Data Spec

- `v`: OTM version
- `tid`: Container ID
- `dl`: current page abstract URL
- `dt`: page title
- `de`: page / document character encoding
- `sd`: screen color depth
- `ul`: user language
- `sr`: screen resolution
- `vp`: viewport size
- `t`: event target
- `cid`: user session UUID, this value is saved on Cookie
- `ec`: event category name
- `ea`: event action name
- `el` (optional): event label
- `o_cts`: client timestamp (ms, unix timestamp)
- `o_pl`: previous page URL
- `o_psid`: page view session UUID
- `o_ps`: previous state, see state format spec
- `o_s`: current state, see state format spec
- `o_r`: UUID for collect data
- `o_xpath` (optional): event xpath data
- `o_tag` (optional): event target tag
- `o_a_*` (optional): event target attributes
- `o_e_*` (optional): event data
  - `x`
  - `y`
  - `rl`: target rect left (px)
  - `rt`: target rect top (px)
  - `rw`: target rect width (px)
  - `rh`: target rect height (px)

## State Format Spec

State data is based on `ea` data. Additionally, some event has suffix.

### click event

`click[_id=${id}][_class=${class}]`

### change-url event

`change-url_url=${url}`
