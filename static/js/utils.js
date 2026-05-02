// Componente Alpine.js reutilizable para formularios con líneas de productos
function lineItems(initialItems) {
  // Normaliza items que vengan de la BD (pedidos pre-cargados)
  const normalize = (raw) => {
    const cant  = parseFloat(raw.cantidad || 1);
    const precio = parseFloat(raw.precio_unitario || raw.precio_venta || 0);
    return {
      id_producto:     raw.id_producto || '',
      nombre:          raw.nombre || '',
      cantidad:        cant,
      precio_unitario: precio,
      aplica_iva:      Boolean(raw.aplica_iva),
      subtotal:        cant * precio,
      query:           raw.nombre || '',
      resultados:      [],
      buscando:        false,
    };
  };

  return {
    items: (initialItems || []).map(normalize),
    descuento: 0,
    ivaRate: 0.15,

    addItem() {
      this.items.push({
        id_producto: '',
        nombre: '',
        cantidad: 1,
        precio_unitario: 0,
        aplica_iva: false,
        subtotal: 0,
        query: '',
        resultados: [],
        buscando: false,
      });
    },

    removeItem(index) {
      this.items.splice(index, 1);
    },

    updateSubtotal(index) {
      const item = this.items[index];
      item.subtotal = parseFloat(item.cantidad || 0) * parseFloat(item.precio_unitario || 0);
    },

    get subtotalSinIva() {
      return this.items.reduce((s, i) => s + parseFloat(i.subtotal || 0), 0);
    },

    get totalIva() {
      return this.items.reduce((s, i) => {
        return s + (i.aplica_iva ? parseFloat(i.subtotal || 0) * this.ivaRate : 0);
      }, 0);
    },

    get totalFinal() {
      return this.subtotalSinIva - parseFloat(this.descuento || 0) + this.totalIva;
    },

    fmt(v) {
      return parseFloat(v || 0).toFixed(2);
    },

    async buscarProducto(index) {
      const item = this.items[index];
      const q = item.query.trim();
      if (q.length < 2) { item.resultados = []; return; }
      item.buscando = true;
      try {
        const r = await fetch(`/productos/api/buscar?q=${encodeURIComponent(q)}`);
        item.resultados = await r.json();
      } finally {
        item.buscando = false;
      }
    },

    seleccionarProducto(index, prod) {
      const item = this.items[index];
      item.id_producto      = prod.id_producto;
      item.nombre           = prod.nombre;
      item.precio_unitario  = prod.precio_venta;
      item.aplica_iva       = prod.aplica_iva;
      item.query            = prod.nombre;
      item.resultados       = [];
      this.updateSubtotal(index);
    },

    // Serializa items como campos hidden antes de submit
    serializarItems() {
      const contenedor = document.getElementById('items-hidden');
      contenedor.innerHTML = '';
      this.items.forEach((item, i) => {
        ['id_producto', 'cantidad', 'precio_unitario'].forEach(campo => {
          const inp = document.createElement('input');
          inp.type  = 'hidden';
          inp.name  = `productos[${i}][${campo}]`;
          inp.value = item[campo];
          contenedor.appendChild(inp);
        });
      });
      return true; // permite el submit
    },
  };
}

// Formatear números como moneda
function moneda(v) {
  return '$ ' + parseFloat(v || 0).toFixed(2);
}
