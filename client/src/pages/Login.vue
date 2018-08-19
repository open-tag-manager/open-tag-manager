<template>
  <div class="container py-2">
    <b-card class="login-form mx-auto">
      <h2>Sign in</h2>
      <form @submit.prevent="login">
        <div class="form-group">
          <label for="username">Username</label>
          <input class="form-control" v-model="username" type="text" id="username" placeholder="username" required>
        </div>

        <div class="form-group">
          <label for="password">Password</label>
          <input class="form-control" v-model="password" type="password" id="password" placeholder="password" required>
        </div>

        <button type="submit" class="btn btn-primary btn-block">Sign in</button>
      </form>
    </b-card>
  </div>
</template>

<script>
  export default {
    data () {
      return {
        username: '',
        password: ''
      }
    },
    methods: {
      async login () {
        await this.$store.dispatch('user/login', {
          username: this.username,
          password: this.password
        })
        this.$router.push('/')
      }
    }
  }
</script>

<style scoped>
  .login-form {
    max-width: 400px;
  }
</style>
