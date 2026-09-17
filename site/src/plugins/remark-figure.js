// Transforme un paragraphe ne contenant qu'une image titrée en figure légendée :
//   ![alt](chemin.png "Légende")  ->  <figure><img ...><figcaption>Légende</figcaption></figure>
// La numérotation « Figure n » est assurée par un compteur CSS.

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
          children: [{type: 'text', value: image.title}],
        },
      ];
      image.title = null;
    });
  };
}
