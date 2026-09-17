// Transforme un paragraphe ne contenant qu'une image titrée en figure légendée :
//   ![alt](chemin.png "Légende")  ->  <figure><img ...><figcaption>Légende</figcaption></figure>
// La numérotation « Figure n » est assurée par un compteur CSS.

/**
 * Découpe une légende en texte et formules `$...$`. Les formules deviennent des nœuds
 * `inlineMath` déjà marqués pour rehype-katex, comme ceux que produit remark-math.
 */
function captionChildren(caption) {
  const children = [];
  let last = 0;
  for (const match of caption.matchAll(/\$([^$\n]+)\$/g)) {
    if (match.index > last) children.push({type: 'text', value: caption.slice(last, match.index)});
    children.push({
      type: 'inlineMath',
      value: match[1],
      data: {
        hName: 'code',
        hProperties: {className: ['language-math', 'math-inline']},
        hChildren: [{type: 'text', value: match[1]}],
      },
    });
    last = match.index + match[0].length;
  }
  if (last < caption.length) children.push({type: 'text', value: caption.slice(last)});
  return children;
}

function visit(node, callback) {
  callback(node);
  if (node.children) node.children.forEach((child) => visit(child, callback));
}

export default function remarkFigure() {
  return (tree) => {
    visit(tree, (node) => {
      if (node.type !== 'paragraph') return;
      const children = node.children.filter((c) => !(c.type === 'text' && c.value.trim() === ''));
      if (children.length !== 1 || children[0].type !== 'image' || !children[0].title) return;
      const image = children[0];
      node.data = {...node.data, hName: 'figure', hProperties: {className: ['lab-figure']}};
      node.children = [
        image,
        {
          type: 'paragraph',
          data: {hName: 'figcaption'},
          children: captionChildren(image.title),
        },
      ];
      image.title = null;
    });
  };
}
