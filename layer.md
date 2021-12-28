# Layer event

You can perform OTM related operation via JavaScript Array object `otmLayer` that is defined on global (`window`).
This operation is allowed before the OTM collector script is loaded.

If `otmLayer` is not defined, you need to define it before using it.

```js
window.otmLayer = window.otmLayer || []
```

## `otm.setuser`

Set the user ID. 

This is used when you want to collect and summarize the user information used in this service.

```js
otmLayer.push({
  event: 'otm.setuser',
  // unique user id for your service
  uid: 'example'
})
```

## `otm.unsetuser`

Unset the user ID.

```js
otmLayer.push({
  event: 'otm.unsetuser'
})
```

## `otm.init`

Initialize OTM.
This is automatically executed for scripts created by the administration client app, so you don't need to run it normally.

```js
otmLayer.push({
  event: 'otm.init',
  // Your collect target URL
  collect: 'http://example.com/collect',
  // Configuration
  config: {}
})
```
