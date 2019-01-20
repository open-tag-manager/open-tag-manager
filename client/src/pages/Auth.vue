<template>
  <div class="container py-4">
    <authenticator :authConfig="{signInConfig: {isSignUpDisplayed: false}}" class="text-center"></authenticator>
  </div>
</template>

<script>
  import {components} from 'aws-amplify-vue'

  export default {
    components: {...components}
  }
</script>
