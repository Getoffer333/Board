declare module 'vuedraggable' {
  import { DefineComponent } from 'vue'
  const draggable: DefineComponent<Record<string, any>, Record<string, any>, any>
  export default draggable
}
