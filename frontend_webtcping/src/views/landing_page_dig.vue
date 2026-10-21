<template>
  <div>
    <landing_page_dig></landing_page_dig>
  </div>
</template>

<script>
// @ is an alias to /src
import landing_page_dig from "@/components/landing_page/tcping/landing_page_dig.vue";

export default {
  name: "Home",
  components: {
    landing_page_dig,
  },
};
</script>
