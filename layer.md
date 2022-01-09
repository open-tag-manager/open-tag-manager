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

If you want to verify that the `uid` passed is correct, you can also send a `uhash` created based on the hash key set in the container.
Since the hash key needs to be kept secret, the `uhash` needs to be generated server-side.

The uhash can be generated as follows:

(PHP)

```php
$uhash = hash_hmac(
  'sha256', // hash function
  'uid', // uid
  'hash_key' // the hash key that is associated with container (keep secret)
);
```

(Python)

```python
import hmac
import hashlib

uhash = hmac.new(
  b'hash_key', # the hash key that is associated with container (keep secret)
  bytes('uid', encoding='utf-8'), # uid
  digestmod=hashlib.sha256
).hexdigest()
```

And send it like this:

```js
otmLayer.push({
  event: 'otm.setuser',
  // unique user id for your service
  uid: 'example',
  // set uhash that is created by server
  uhash: 'ee8aba1afcb089f8979c50a663266a11c8f52d8b712f3874e10b26a04902a6be'
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
