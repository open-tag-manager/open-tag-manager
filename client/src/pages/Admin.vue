<template>
  <div>
    <div class="container-fluid">
      <div class="row">
        <div class="col-2 bg-light sidebar py-4">
          <b-nav vertical>
            <b-nav-item :to="{name: 'Admin-Orgs'}">
              Orgs
            </b-nav-item>
            <b-nav-item :to="{name: 'Admin-Users'}">
              Users
            </b-nav-item>
          </b-nav>
        </div>
        <div role="main" class="col-10 px-4">
          <router-view></router-view>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
  export default {
    async mounted () {
      if (this.$route.name === 'Admin') {
        this.$router.replace({name: 'Admin-Orgs'})
      }
    }
  }
</script>

<style scoped>
  .sidebar {
    position: sticky;
    z-index: 1000;
    top: 56px;
    height: calc(100vh - 56px);
    overflow: scroll;
  }

  .router-link-active {
    font-weight: bold;
  }
</style>
