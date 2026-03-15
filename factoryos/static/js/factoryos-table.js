document.addEventListener("DOMContentLoaded", function () {

const tables = document.querySelectorAll(".fos-table")

tables.forEach(table => {

const tableId = table.id
const wrapper = table.closest(".fos-table-wrapper")

const searchInput = wrapper.querySelector(".fos-search")

if(searchInput){

searchInput.addEventListener("keyup", function(){

const value = searchInput.value.toLowerCase()

const rows = table.querySelectorAll("tbody tr")

rows.forEach(row => {

const text = row.innerText.toLowerCase()

row.style.display = text.includes(value) ? "" : "none"

})

})

}


/* SORTING */

const headers = table.querySelectorAll("th")

headers.forEach((header,i)=>{

let asc = true

header.addEventListener("click",()=>{

const tbody = table.querySelector("tbody")

const rows = Array.from(tbody.querySelectorAll("tr"))

rows.sort((a,b)=>{

const A = a.children[i].innerText.toLowerCase()
const B = b.children[i].innerText.toLowerCase()

return asc
? A.localeCompare(B)
: B.localeCompare(A)

})

asc = !asc

rows.forEach(r=>tbody.appendChild(r))

})

})


/* PAGINATION */

const rows = table.querySelectorAll("tbody tr")

const pagination = wrapper.querySelector(".fos-pagination")

if(!pagination) return

const perPage = 10

let page = 1

function render(){

rows.forEach((row,i)=>{

row.style.display =
(i >= (page-1)*perPage && i < page*perPage)
? ""
: "none"

})

}

function createButtons(){

const pages = Math.ceil(rows.length / perPage)

pagination.innerHTML = ""

for(let i=1;i<=pages;i++){

const btn = document.createElement("div")

btn.className = "fos-page-btn"
btn.innerText = i

btn.onclick = ()=>{

page = i

wrapper
.querySelectorAll(".fos-page-btn")
.forEach(b=>b.classList.remove("active"))

btn.classList.add("active")

render()

}

if(i===1) btn.classList.add("active")

pagination.appendChild(btn)

}

}

createButtons()
render()

})

})