import { Vue } from 'vue-property-decorator'

export default class Org extends Vue {
  get currentOrg(): string {
    return this.$route.params.name
  }
}
