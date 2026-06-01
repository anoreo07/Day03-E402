let PRODUCTS = []
let CART = {}
let LAST_TOTAL = 0

const categoryHints = {
  Electronics: 'EL',
  Accessories: 'AC',
  Travel: 'TR',
  Home: 'HM',
  Fitness: 'FT',
  Fashion: 'FA',
  Beauty: 'BE',
  Toys: 'TO',
  Pet: 'PE'
}

const formatCurrency = (n) => `$${Number(n || 0).toFixed(2)}`

async function loadProducts() {
  const res = await fetch('/api/products')
  PRODUCTS = await res.json()
  renderProducts(PRODUCTS)
  renderRecommendations(getRecommendedProducts())
  renderCart()
}

function getRecommendedProducts(query = '') {
  const normalized = query.toLowerCase()
  let items = PRODUCTS

  if (normalized.includes('electronics') || normalized.includes('tai nghe') || normalized.includes('charger') || normalized.includes('keyboard')) {
    items = PRODUCTS.filter(p => p.category === 'Electronics')
  } else if (normalized.includes('dưới 50') || normalized.includes('under 50') || normalized.includes('$50')) {
    items = PRODUCTS.filter(p => Number(p.price_usd) <= 50)
  } else if (normalized.includes('home') || normalized.includes('nhà') || normalized.includes('bếp')) {
    items = PRODUCTS.filter(p => p.category === 'Home')
  } else if (normalized.includes('fashion') || normalized.includes('giày') || normalized.includes('áo')) {
    items = PRODUCTS.filter(p => p.category === 'Fashion')
  }

  return [...items]
    .sort((a, b) => Number(b.stock_qty) - Number(a.stock_qty))
    .slice(0, 3)
}

function productInitial(product) {
  return categoryHints[product.category] || product.name.slice(0, 2).toUpperCase()
}

function renderRecommendations(items) {
  const el = document.getElementById('recommended-products')
  el.innerHTML = ''

  if (!items.length) {
    el.innerHTML = '<div class="empty-state"><p>Chưa có gợi ý phù hợp. Hãy thử hỏi trợ lý theo ngân sách hoặc danh mục.</p></div>'
    return
  }

  items.forEach(p => {
    const card = document.createElement('div')
    card.className = 'mini-product'
    card.innerHTML = `
      <div class="product-thumb">${productInitial(p)}</div>
      <div>
        <p class="product-name">${p.name}</p>
        <p class="product-meta">${p.category} · ${p.stock_qty} còn hàng · ${p.coupon_code}</p>
      </div>
      <div>
        <div class="price">${formatCurrency(p.price_usd)}</div>
        <button class="btn ghost" data-add="${p.product_id}" data-qty="1">Thêm</button>
      </div>
    `
    el.appendChild(card)
  })

  bindAddButtons(el)
}

function renderProducts(items) {
  const el = document.getElementById('products')
  el.innerHTML = ''

  if (!items.length) {
    el.innerHTML = '<div class="empty-state"><p>Không tìm thấy sản phẩm phù hợp.</p></div>'
    return
  }

  items.forEach(p => {
    const card = document.createElement('div')
    card.className = 'product-card'
    card.innerHTML = `
      <div class="product-top">
        <div class="product-visual">${productInitial(p)}</div>
        <div>
          <p class="product-name">${p.name}</p>
          <p class="product-meta">${p.category} · ${p.stock_qty} có sẵn</p>
        </div>
      </div>
      <div class="price">${formatCurrency(p.price_usd)}</div>
      <div class="coupon-tag">Coupon ${p.coupon_code}</div>
      <div class="product-actions">
        <input class="product-qty" type="number" min="1" value="1" data-pid="${p.product_id}" aria-label="Số lượng ${p.name}" />
        <button class="btn primary" data-add="${p.product_id}">Thêm vào giỏ</button>
      </div>
    `
    el.appendChild(card)
  })

  bindAddButtons(el)
}

function bindAddButtons(scope = document) {
  scope.querySelectorAll('[data-add]').forEach(btn => {
    btn.addEventListener('click', async e => {
      const pid = e.currentTarget.dataset.add
      const qtyInput = document.querySelector(`input[data-pid="${pid}"]`)
      const quickQty = Number(e.currentTarget.dataset.qty || 0)
      const qty = Math.max(1, quickQty || parseInt(qtyInput?.value || 1))
      const product = PRODUCTS.find(p => p.product_id === pid)

      CART[pid] = (CART[pid] || 0) + qty
      if (qtyInput) qtyInput.value = 1
      appendChat('bot', `Đã thêm ${qty} × ${product.name} vào giỏ. Bạn có thể áp mã ${product.coupon_code} để kiểm tra ưu đãi.`)
      await renderCart()
    })
  })
}

function renderCart() {
  const el = document.getElementById('cart-items')
  const cartKeys = Object.keys(CART)
  const cartCount = cartKeys.reduce((sum, pid) => sum + CART[pid], 0)
  document.getElementById('cart-count').innerText = `${cartCount} món`
  document.getElementById('step-cart').classList.toggle('active', cartCount > 0)

  el.innerHTML = ''
  if (!cartKeys.length) {
    el.innerHTML = '<div class="empty-state"><p>Giỏ hàng trống. Thêm sản phẩm từ gợi ý hoặc catalog để bắt đầu.</p></div>'
    recalc()
    return
  }

  cartKeys.forEach(pid => {
    const p = PRODUCTS.find(x => x.product_id === pid)
    if (!p) return

    const qty = CART[pid]
    const row = document.createElement('div')
    row.className = 'cart-item'
    row.innerHTML = `
      <div class="cart-item-header">
        <div>
          <p class="cart-item-title">${p.name}</p>
          <p class="cart-item-meta">${qty} × ${formatCurrency(p.price_usd)} · mã ${p.coupon_code}</p>
        </div>
        <div class="price">${formatCurrency(p.price_usd * qty)}</div>
      </div>
      <div class="cart-tools">
        <div class="qty-tools">
          <button class="btn ghost qty-btn" data-action="decrease" data-pid="${pid}" aria-label="Giảm ${p.name}">-</button>
          <button class="btn ghost qty-btn" data-action="increase" data-pid="${pid}" aria-label="Tăng ${p.name}">+</button>
        </div>
        <button class="btn ghost" data-remove="${pid}">Xóa</button>
      </div>
    `
    el.appendChild(row)
  })

  document.querySelectorAll('[data-remove]').forEach(btn => {
    btn.addEventListener('click', e => {
      delete CART[e.currentTarget.dataset.remove]
      renderCart()
    })
  })

  document.querySelectorAll('[data-action]').forEach(btn => {
    btn.addEventListener('click', e => {
      const pid = e.currentTarget.dataset.pid
      const action = e.currentTarget.dataset.action
      if (action === 'increase') CART[pid] = (CART[pid] || 0) + 1
      if (action === 'decrease') {
        CART[pid] = Math.max(0, (CART[pid] || 0) - 1)
        if (CART[pid] === 0) delete CART[pid]
      }
      renderCart()
    })
  })

  recalc()
}

async function recalc() {
  const cart = Object.keys(CART).map(pid => ({ product_id: pid, qty: CART[pid] }))
  const coupon = document.getElementById('coupon').value.trim()
  const res = await fetch('/api/price', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cart, coupon_code: coupon })
  })
  const data = await res.json()
  LAST_TOTAL = data.total || 0

  document.getElementById('subtotal').innerText = formatCurrency(data.subtotal)
  document.getElementById('shipping').innerText = formatCurrency(data.shipping)
  document.getElementById('tax').innerText = formatCurrency(data.tax)
  document.getElementById('discount').innerText = `-${formatCurrency(data.discount)}`
  document.getElementById('total').innerText = formatCurrency(data.total)
  document.getElementById('step-coupon').classList.toggle('active', Boolean(data.applied_coupon))
}

function filterProducts(query) {
  const normalized = query.trim().toLowerCase()
  if (!normalized) {
    renderProducts(PRODUCTS)
    renderRecommendations(getRecommendedProducts())
    return
  }

  const filtered = PRODUCTS.filter(p => {
    return p.name.toLowerCase().includes(normalized) || p.category.toLowerCase().includes(normalized)
  })
  renderProducts(filtered)
  renderRecommendations(getRecommendedProducts(query))
}

function appendChat(role, content) {
  const chatWindow = document.getElementById('chat-window')
  const bubble = document.createElement('div')
  bubble.className = `message ${role}`
  bubble.innerHTML = role === 'bot'
    ? `<span class="message-label">MiniMart AI</span>${content}`
    : content
  chatWindow.appendChild(bubble)
  chatWindow.scrollTop = chatWindow.scrollHeight
}

function bestCouponProduct() {
  return [...PRODUCTS].sort((a, b) => Number(b.coupon_discount_pct || 0) - Number(a.coupon_discount_pct || 0))[0]
}

function generateAssistantReply(message) {
  const lower = message.toLowerCase()
  const recommendations = getRecommendedProducts(message)
  renderRecommendations(recommendations)

  if (lower.includes('đặt hàng') || lower.includes('checkout') || lower.includes('order')) {
    return 'Bạn thêm sản phẩm vào giỏ, nhập coupon nếu có, rồi bấm "Đặt hàng giả lập". Mình sẽ tạo receipt demo ngay trên màn hình.'
  }
  if (lower.includes('giảm giá') || lower.includes('coupon') || lower.includes('mã')) {
    const p = bestCouponProduct()
    return `Mã nổi bật hôm nay là ${p.coupon_code} cho ${p.name}. Bạn cũng có thể dùng coupon hiển thị trên từng sản phẩm trong catalog.`
  }
  if (lower.includes('tồn kho') || lower.includes('còn hàng') || lower.includes('còn')) {
    const top = recommendations[0]
    return top
      ? `${top.name} đang còn ${top.stock_qty} sản phẩm. Mình đã đưa các lựa chọn còn hàng vào khung gợi ý bên phải.`
      : 'Mình chưa tìm thấy sản phẩm khớp yêu cầu. Bạn thử nhập tên hoặc danh mục cụ thể hơn nhé.'
  }
  if (lower.includes('dưới 50') || lower.includes('under 50') || lower.includes('$50')) {
    return 'Mình đã lọc các món dưới $50 ở khung gợi ý. Các lựa chọn tốt gồm phụ kiện, đồ gia dụng nhỏ và một số sản phẩm electronics.'
  }
  if (lower.includes('electronics') || lower.includes('tai nghe') || lower.includes('laptop') || lower.includes('keyboard')) {
    return 'Mình ưu tiên nhóm Electronics còn hàng, có coupon và dễ thêm vào giỏ. Bạn xem khung gợi ý bên phải để chọn nhanh.'
  }
  return 'Mình đã cập nhật gợi ý theo yêu cầu. Bạn có thể nói rõ ngân sách, danh mục hoặc mục đích sử dụng để mình lọc chính xác hơn.'
}

function handleAssistant(textFromButton) {
  const input = document.getElementById('assistant-input')
  const text = (textFromButton || input.value).trim()
  if (!text) return

  appendChat('user', text)
  input.value = ''
  const reply = generateAssistantReply(text)
  setTimeout(() => appendChat('bot', reply), 260)
}

function applyCoupon() {
  const coupon = document.getElementById('coupon').value.trim()
  recalc()
  if (coupon) appendChat('bot', `Mình đã kiểm tra mã ${coupon}. Nếu đơn hàng đủ điều kiện, tổng tiền đã được cập nhật ở Order summary.`)
}

function openOrderModal() {
  const cartKeys = Object.keys(CART)
  if (!cartKeys.length) {
    appendChat('bot', 'Giỏ hàng đang trống. Bạn thêm ít nhất một sản phẩm rồi mình sẽ tạo đơn hàng giả lập nhé.')
    return
  }

  document.getElementById('step-order').classList.add('active')
  const itemCount = cartKeys.reduce((sum, pid) => sum + CART[pid], 0)
  const receipt = document.getElementById('order-receipt')
  receipt.innerHTML = `
    <strong>Mã đơn:</strong> MOCK-${Date.now().toString().slice(-6)}<br>
    <strong>Số lượng:</strong> ${itemCount} món<br>
    <strong>Tổng thanh toán:</strong> ${formatCurrency(LAST_TOTAL)}<br>
    <strong>Trạng thái:</strong> Đơn demo đã được tạo, không phát sinh thanh toán thật.
  `

  document.getElementById('order-modal').classList.add('open')
  document.getElementById('order-modal').setAttribute('aria-hidden', 'false')
}

function closeOrderModal() {
  document.getElementById('order-modal').classList.remove('open')
  document.getElementById('order-modal').setAttribute('aria-hidden', 'true')
}

document.getElementById('apply-coupon').addEventListener('click', applyCoupon)
document.getElementById('checkout').addEventListener('click', openOrderModal)
document.getElementById('close-modal').addEventListener('click', closeOrderModal)
document.getElementById('continue-shopping').addEventListener('click', closeOrderModal)
document.getElementById('order-modal').addEventListener('click', e => {
  if (e.target.id === 'order-modal') closeOrderModal()
})
document.getElementById('assistant-send').addEventListener('click', () => handleAssistant())
document.getElementById('assistant-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') handleAssistant()
})
document.getElementById('search').addEventListener('input', e => filterProducts(e.target.value))
document.querySelectorAll('[data-prompt]').forEach(btn => {
  btn.addEventListener('click', e => handleAssistant(e.currentTarget.dataset.prompt))
})

loadProducts()
