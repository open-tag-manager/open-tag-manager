import Org from '~/components/Org'

export default class OrgContainer extends Org {
  get currentContainer(): string {
    return this.$route.params.container
  }
}
