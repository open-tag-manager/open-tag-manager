import OrgContainer from '~/components/OrgContainer'

export default class OrgContainerStat extends OrgContainer {
  get currentStat(): string {
    return this.$route.params.stat
  }
}
