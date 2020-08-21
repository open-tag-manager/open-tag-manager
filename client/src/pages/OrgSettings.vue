<template>
  <div class="container-fluid">
    <div class="row">
      <div class="col-2 bg-light sidebar py-4">
        <b-nav vertical>
          <b-nav-item :to="{name: 'Org-Settings-Containers', params: {org: $route.params.org}}">
            Containers
          </b-nav-item>
          <b-nav-item :to="{name: 'Org-Settings-Users', params: {org: $route.params.org}}">
            Users
          </b-nav-item>
          <b-nav-item :to="{name: 'Org-Settings-Usage', params: {org: $route.params.org}}">
            Usage
          </b-nav-item>
          <b-nav-item v-for="item in $store.state.orgMenu" :key="item.name" :to="{name: item.name, params: {org: $route.params.org}}">
            {{ item.label }}
          </b-nav-item>
        </b-nav>
      </div>
      <div role="main" class="col-10 px-4">
        <router-view></router-view>
      </div>
    </div>
  </div>
</template>

<script>
  export default {
    async mounted () {
      if (this.$route.name === 'Org-Settings') {
        this.$router.replace({name: 'Org-Settings-Containers', params: {org: this.$route.params.org}})
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
